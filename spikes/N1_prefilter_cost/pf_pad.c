/* N1 — the prefilter's per-query cost, measured directly at the deployable
 * operating point instead of inherited.
 *
 * The workspace's ~50 us figure is flagged by its own note as inheriting
 * S18's overhead artifact, and it is the last rung of the NPU descope. This
 * measures a B=64 shard (12,500 bundles = 1.60 MB, per S11) on the background
 * cpuset, single-threaded and with the bundle range split across T threads.
 *
 * Reports cycles/row as well as us, per LEDGER rule 1: us is a governor
 * reading, cycles/row is not.
 *
 * Build: aarch64-linux-android29-clang -O3 -march=armv8.6-a+i8mm+dotprod \
 *          -ffp-model=fast -o pf pf.c -lm
 */
#define _GNU_SOURCE
#include <arm_neon.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define D 1024
#define WORDS (D/64)
static int NB = 12500;        /* B=64 over 800k triples: S11's 1.60 MB shard.
                               * Override with argv[1] to isolate shard size. */

static uint64_t *Tp, Qs[WORDS], Qm[WORDS];
static int32_t *scores, Qnnz;
static int NT_THREADS;
/* CachePadded, after crossbeam-utils/src/cache_padded.rs:94 (Apache-2.0),
 * which uses align(128) on aarch64 -- ARM prefetches pairs of 64-byte lines.
 * These three atomics were declared adjacent and are the hottest thing in the
 * barrier: every crossing invalidates the line on every core. */
typedef struct { _Alignas(128) atomic_int v; } pad_atomic_t;
static pad_atomic_t gen_p, left_p, stop_p;
#define gen  (gen_p.v)
#define left (left_p.v)
#define stop (stop_p.v)

static double now_s(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
                           return t.tv_sec + t.tv_nsec*1e-9; }
static uint32_t rs=0xC0FFEE;
static uint32_t r32(void){ rs^=rs<<13; rs^=rs>>17; rs^=rs<<5; return rs; }
static uint64_t r64(void){ return ((uint64_t)r32()<<32)|r32(); }

/* measured clock: dependent add chain, 1 retire/cycle. sysfs reports a policy
 * frequency and was seen 27% wrong on this part (S53). */
static double mhz(void){
    uint64_t it=20000000ull, a=0; double t0=now_s();
    __asm__ volatile("1:\n\t" "add %[a],%[a],#1\n\t" "add %[a],%[a],#1\n\t"
        "add %[a],%[a],#1\n\t" "add %[a],%[a],#1\n\t" "add %[a],%[a],#1\n\t"
        "add %[a],%[a],#1\n\t" "add %[a],%[a],#1\n\t" "add %[a],%[a],#1\n\t"
        "subs %[n],%[n],#1\n\t" "b.ne 1b\n\t"
        :[a]"+r"(a),[n]"+r"(it)::"cc");
    double m=(double)(20000000ull*8)/(now_s()-t0)/1e6;
    if(!(m>500&&m<5000)){ fprintf(stderr,"IMPLAUSIBLE CLOCK %.0f MHz\n",m); exit(1); }
    return m;
}
static void rows(long lo,long hi){
    for(long i=lo;i<hi;i++){
        const uint64_t*t=Tp+(size_t)i*WORDS; uint8x16_t v=vdupq_n_u8(0);
        for(int w=0;w<WORDS;w+=2){
            uint64x2_t a=vld1q_u64(t+w),s=vld1q_u64(Qs+w),m=vld1q_u64(Qm+w);
            v=vaddq_u8(v,vcntq_u8(vreinterpretq_u8_u64(vandq_u64(veorq_u64(a,s),m))));
        }
        scores[i]=2*Qnnz-4*(int32_t)vaddlvq_u8(v);
    }
}
typedef struct{int id,cpu;} warg;
static void*worker(void*p){
    warg*w=(warg*)p; cpu_set_t s; CPU_ZERO(&s); CPU_SET(w->cpu,&s);
    sched_setaffinity(0,sizeof s,&s);
    int seen=0;
    for(;;){
        while(atomic_load(&gen)==seen) if(atomic_load(&stop)) return NULL;
        seen=atomic_load(&gen);
        long c=(NB+NT_THREADS-1)/NT_THREADS, lo=(long)w->id*c, hi=lo+c>NB?NB:lo+c;
        if(lo<NB) rows(lo,hi);
        atomic_fetch_sub(&left,1);
    }
}
int main(int argc,char**argv){
    if(argc>1) NB=atoi(argv[1]);
    Tp=malloc((size_t)NB*WORDS*8); scores=malloc((size_t)NB*4);
    for(size_t i=0;i<(size_t)NB*WORDS;i++) Tp[i]=r64();
    for(int w=0;w<WORDS;w++){ Qm[w]=r64(); Qs[w]=r64()&Qm[w]; Qnnz+=__builtin_popcountll(Qm[w]); }
    double f=mhz();
    printf("N1 prefilter cost — B=64 shard, %d bundles = %.2f MB, clock %.0f MHz\n",
           NB, (double)NB*WORDS*8/1e6, f);
    printf("  %8s %12s %14s %12s\n","threads","us/query","cycles/bundle","speedup");
    double base=0;
    /* background cpuset is 0-1,4-5 (S54). Coordinator excluded from the split. */
    static const int cpus[4]={0,1,4,5};
    int NCPUS=4;                 /* background cpuset 0-1,4-5 (S54) */
    for(int T=1;T<=4;T++){
        /* A spin barrier needs a free core for the coordinator. T==NCPUS makes
         * the coordinator timeslice against a worker: measured 337x slower at
         * T=4. S51 hit it at T=8, S53 at T=1, N1 at T=4 -- the rule was in the
         * LEDGER all three times. Refuse rather than remind. */
        if(T>=NCPUS){
            printf("  %8d %12s %14s %11s   REFUSED: spin barrier needs a free core (T>=%d)\n",
                   T,"-","-","-",NCPUS);
            continue;
        }
        NT_THREADS=T; pthread_t th[4]; warg wa[4];
        atomic_store(&gen,0); atomic_store(&stop,0); atomic_store(&left,0);
        for(int i=0;i<T;i++){ wa[i].id=i; wa[i].cpu=cpus[i];
                              pthread_create(&th[i],NULL,worker,&wa[i]); }
        struct timespec ts={0,30000000L}; nanosleep(&ts,NULL);
        double best=1e18;
        for(int k=0;k<9;k++){
            double t0=now_s();
            for(int r=0;r<200;r++){ atomic_store(&left,T); atomic_fetch_add(&gen,1);
                                    while(atomic_load(&left)>0){} }
            double e=(now_s()-t0)/200.0; if(e<best) best=e;
        }
        atomic_store(&stop,1); atomic_fetch_add(&gen,1);
        for(int i=0;i<T;i++) pthread_join(th[i],NULL);
        if(T==1) base=best;
        printf("  %8d %12.1f %14.2f %11.2fx\n", T, best*1e6,
               best*f*1e6/(double)NB, base/best);
    }
    return 0;
}
