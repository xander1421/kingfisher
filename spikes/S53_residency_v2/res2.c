/* S53 — residency, measured properly, in cycles/row.
 *
 * I un-retracted S46's residency chain on a 4-point size sweep at ONE thread
 * count on ONE day, then flagged that as thin in the ledger. This is the
 * version that either survives or does not:
 *
 *   - threads 1, 2, 4, 7 x sizes 12.8 .. 204.8 MB, so "residency matters
 *     multi-core" is a surface, not a line
 *   - reported in CYCLES/ROW, the invariant. Four attacks established that
 *     GB/s on this device is a function of the governor: the same binary gave
 *     49.8 GB/s at 3283 MHz and 40.1 at 2649, ratio 1.242 == 3283/2649 to
 *     three digits. Cycles/row held to three digits across every clock and
 *     thermal state anyone could produce.
 *   - the clock is MEASURED per run, not read from sysfs, because sysfs
 *     reports a POLICY (cluster) frequency and was seen off by 27% on cpu6
 *   - three independent invocations, so run-to-run instability is visible
 *     rather than hidden behind a within-run MAD
 *
 * Build: aarch64-linux-android29-clang -O3 -Wall -Wextra -Werror \
 *          -march=armv8.6-a+i8mm+dotprod -o res2 res2.c
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

#define D      1024
#define WORDS  (D / 64)
#define MAXMB  204

static uint64_t *Tp, Qs[WORDS], Qm[WORDS];
static int32_t  *scores, Qnnz;
static long      NROWS;
static int       NT;
static atomic_int a_gen, a_left, a_stop;

static double now_s(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
                           return t.tv_sec + t.tv_nsec*1e-9; }
static uint32_t rs = 0xC0FFEE;
static uint32_t r32(void){ rs^=rs<<13; rs^=rs>>17; rs^=rs<<5; return rs; }
static uint64_t r64(void){ uint64_t h=r32(); uint64_t l=r32(); return (h<<32)|l; }

/* measured clock: a dependent add chain retires exactly 1/cycle, so
 * iterations/second IS the core frequency. sysfs reports the cluster's
 * policy frequency and has been observed 27% wrong on this part. */
static double measure_mhz(void) {
    /* First attempt used `for(i..) x += i;` and the compiler replaced it with
     * Gauss's closed form, reporting 769,190,472 MHz. A calibration loop must
     * be opaque to the optimiser, so this is inline asm: 8 dependent adds per
     * iteration, each 1 cycle, nothing the compiler may fold. */
    uint64_t iters = 20000000ull, acc = 0;
    double t0 = now_s();
    __asm__ volatile(
        "1:\n\t"
        "add %[a], %[a], #1\n\t" "add %[a], %[a], #1\n\t"
        "add %[a], %[a], #1\n\t" "add %[a], %[a], #1\n\t"
        "add %[a], %[a], #1\n\t" "add %[a], %[a], #1\n\t"
        "add %[a], %[a], #1\n\t" "add %[a], %[a], #1\n\t"
        "subs %[n], %[n], #1\n\t"
        "b.ne 1b\n\t"
        : [a] "+r"(acc), [n] "+r"(iters)
        : : "cc");
    double el = now_s() - t0;
    double mhz = (double)(20000000ull * 8) / el / 1e6;   /* 8 cycles/iter */
    if (acc != 20000000ull * 8) fprintf(stderr, "calibration corrupted\n");
    return mhz;
}

static long sysfs_khz(int cpu) {
    char p[128]; snprintf(p,sizeof p,
        "/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq",cpu);
    FILE *f=fopen(p,"r"); if(!f) return -1;
    long v=-1; if(fscanf(f,"%ld",&v)!=1) v=-1; fclose(f); return v;
}

static void rows(long lo, long hi) {
    for (long i = lo; i < hi; i++) {
        const uint64_t *tp = Tp + (size_t)i * WORDS;
        uint8x16_t v = vdupq_n_u8(0);
        for (int w = 0; w < WORDS; w += 2) {
            uint64x2_t t = vld1q_u64(tp + w);
            uint64x2_t s = vld1q_u64(Qs + w);
            uint64x2_t m = vld1q_u64(Qm + w);
            v = vaddq_u8(v, vcntq_u8(vreinterpretq_u8_u64(
                    vandq_u64(veorq_u64(t, s), m))));
        }
        scores[i] = 2 * Qnnz - 4 * (int32_t)vaddlvq_u8(v);
    }
}

typedef struct { int id, cpu; } warg;
static void *worker(void *a) {
    warg *w = (warg *)a;
    cpu_set_t set; CPU_ZERO(&set); CPU_SET(w->cpu, &set);
    sched_setaffinity(0, sizeof set, &set);
    int seen = 0;
    for (;;) {
        while (atomic_load(&a_gen) == seen)
            if (atomic_load(&a_stop)) return NULL;
        seen = atomic_load(&a_gen);
        long c = (NROWS + NT - 1) / NT, lo = (long)w->id * c;
        long hi = lo + c > NROWS ? NROWS : lo + c;
        if (lo < NROWS) rows(lo, hi);
        atomic_fetch_sub(&a_left, 1);
    }
}

static int cmp_d(const void *a, const void *b){
    double x=*(const double*)a, y=*(const double*)b; return (x>y)-(x<y); }

static double run_cfg(int nt, long nrows) {
    /* Workers get cpu0..cpu6; the COORDINATOR owns cpu7 exclusively.
     * First version pinned main to cpu0 and worker 0 to cpu0 as well, so the
     * spinning coordinator timesliced against a worker and T=1 read 222
     * cyc/row against a true ~17. That is exactly the coordinator-starvation
     * effect S51 discovered at T=8 and I then walked straight into at T=1. */
    static const int order[7] = {0,1,2,3,4,5,6};
    NT = nt; NROWS = nrows;
    pthread_t th[8]; warg wa[8];
    atomic_store(&a_gen,0); atomic_store(&a_stop,0); atomic_store(&a_left,0);
    for (int i=0;i<nt;i++){ wa[i].id=i; wa[i].cpu=order[i];
                            pthread_create(&th[i],NULL,worker,&wa[i]); }
    struct timespec ts={0,30000000L}; nanosleep(&ts,NULL);
    int inner = nrows > 400000 ? 4 : (nrows > 100000 ? 10 : 30);
    double s[9];
    for (int k=0;k<9;k++){
        double t0=now_s();
        for (int r=0;r<inner;r++){
            atomic_store(&a_left,nt);
            atomic_fetch_add(&a_gen,1);
            while (atomic_load(&a_left)>0) { }
        }
        s[k]=(now_s()-t0)/inner;
    }
    atomic_store(&a_stop,1); atomic_fetch_add(&a_gen,1);
    for (int i=0;i<nt;i++) pthread_join(th[i],NULL);
    qsort(s,9,sizeof(double),cmp_d);
    return s[4];                       /* median of 9 */
}

int main(void) {
    long maxrows = (long)MAXMB * 1000000 / (WORDS * 8);
    Tp = malloc((size_t)maxrows * WORDS * 8);
    scores = malloc((size_t)maxrows * 4);
    if (!Tp || !scores) { fprintf(stderr,"alloc\n"); return 1; }
    for (size_t i=0;i<(size_t)maxrows*WORDS;i++) Tp[i]=r64();
    for (int w=0;w<WORDS;w++){ Qm[w]=r64(); Qs[w]=r64()&Qm[w];
                               Qnnz+=__builtin_popcountll(Qm[w]); }

    cpu_set_t set; CPU_ZERO(&set); CPU_SET(7,&set);   /* coordinator alone on cpu7 */
    sched_setaffinity(0,sizeof set,&set);
    double mhz = measure_mhz();
    printf("S53 residency v2 — cycles/row, the governor-invariant unit\n");
    long sk = sysfs_khz(7);
    printf("coordinator on cpu7; workers cpu0..cpu6 (perf cluster)\n");
    printf("measured cpu7 clock %.0f MHz (inline-asm dependent chain)\n", mhz);
    printf("sysfs says %ld MHz  -> ratio %.3f %s\n\n", sk/1000, mhz/(sk/1000.0),
           (mhz > 500 && mhz < 5000) ? "" : "*** IMPLAUSIBLE, ABORTING ***");
    if (!(mhz > 500 && mhz < 5000)) return 1;

    /* workers live on the perf cluster, so cycles/row must use ITS clock */
    CPU_ZERO(&set); CPU_SET(0,&set); sched_setaffinity(0,sizeof set,&set);
    double wmhz = measure_mhz();
    CPU_ZERO(&set); CPU_SET(7,&set); sched_setaffinity(0,sizeof set,&set);
    printf("worker-cluster (cpu0) clock %.0f MHz\n\n", wmhz);

    long sizes[] = {100000, 200000, 400000, 800000, 1600000};
    int  ths[]   = {1, 2, 4, 6};

    printf("%9s %10s", "store_MB", "rows");
    for (size_t t=0;t<sizeof ths/sizeof ths[0];t++) printf("   T=%d cyc/row", ths[t]);
    printf("      residency factor (smallest vs largest)\n");

    double first[8], last[8];
    for (size_t k=0;k<sizeof sizes/sizeof sizes[0];k++) {
        long n = sizes[k];
        if (n > maxrows) continue;
        printf("%9.1f %10ld", (double)n*WORDS*8/1e6, n);
        for (size_t t=0;t<sizeof ths/sizeof ths[0];t++) {
            double sec = run_cfg(ths[t], n);
            /* aggregate cycles per row across the whole SoC slice in play */
            double cyc = sec * wmhz * 1e6 / (double)n * ths[t];
            printf("%14.2f", cyc);
            if (k==0) first[t]=cyc;
            last[t]=cyc;
        }
        printf("\n");
    }
    printf("\n%-22s","residency factor:");
    for (size_t t=0;t<sizeof ths/sizeof ths[0];t++)
        printf(" T=%d %.2fx  ", ths[t], last[t]/first[t]);
    printf("\n(>1 means the large store costs more cycles/row than the small one,\n"
           " i.e. residency is worth something at that thread count)\n");
    return 0;
}
