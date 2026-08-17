/* S51 — the multi-core number the fleet model has been resting on, measured
 * properly for the first time.
 *
 * S50 closed by admitting there is no defensible multi-threaded throughput
 * figure in this workspace. S32's 5.87x scaling, S45b's 50.8 GB/s and the
 * 28,700 jobs/s fleet projection all descend from harnesses that put
 * pthread_create inside the timed region, used a ~40 us condvar barrier, and
 * never pinned a thread. S50 then measured 2.26x between core types on one
 * core, which means an unpinned thread pool is a lottery over a 2.26x spread.
 *
 * This measures:
 *   - a SPIN barrier (atomics, no futex) instead of the condvar
 *   - one thread PINNED per core, explicitly chosen
 *   - amortised: many kernel passes inside one timing bracket
 *   - STATIC equal chunks vs DYNAMIC work-stealing, because the SoC is
 *     heterogeneous (cpu0-5 max 3.53 GHz, cpu6-7 max 4.47 GHz) and equal
 *     chunks make the slow cores stragglers while the fast ones idle
 *   - the barrier's own cost, measured with an empty kernel, so the null is
 *     reported rather than assumed
 *   - a digest over every row, compared across thread counts and strategies:
 *     parallelism must not change the answer
 *
 * Build: aarch64-linux-android29-clang -O3 -Wall -Wextra -Werror \
 *          -march=armv8.6-a+i8mm+dotprod -o mc mc.c -lm
 */

#define _GNU_SOURCE
#include <arm_neon.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define D      1024
#define WORDS  (D / 64)
#define NROWS  100000
#define MAXT   8
#define REPS   11
#define CHUNK  512            /* rows per dynamic work-stealing claim */

static uint64_t *Tp, Qs[WORDS], Qm[WORDS];
static int32_t  *scores, Qnnz;

static double now_s(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}
static uint32_t rng_s = 0xC0FFEE;
static uint32_t r32(void) { rng_s ^= rng_s << 13; rng_s ^= rng_s >> 17;
                            rng_s ^= rng_s << 5;  return rng_s; }
static uint64_t r64(void) { uint64_t hi = r32(); uint64_t lo = r32();
                            return (hi << 32) | lo; }

/* ---- spin barrier: two atomics, no kernel involvement ------------------ */
/* N1e: b_cursor is the work-stealing claim counter; b_left is spun on by the
 * coordinator for the WHOLE work phase. Different variables, concurrent
 * access, one line -> false sharing. PAD=1 moves the cursor off that line.
 * Static mode never touches the cursor: same-binary negative control. */
#ifndef PAD
#define PAD 0
#endif
typedef struct {
    atomic_int  gen, left, stop, dyn, empty;
#if PAD
    char        _pad[128];
#endif
    atomic_long cursor;
} bstate_t;
static bstate_t BS __attribute__((aligned(128)));
#define b_gen    BS.gen
#define b_left   BS.left
#define b_stop   BS.stop
#define b_dyn    BS.dyn
#define b_empty  BS.empty
#define b_cursor BS.cursor
static int         b_nthreads;

static void kernel_rows(long lo, long hi) {
    for (long i = lo; i < hi; i++) {
        const uint64_t *tp = Tp + (size_t)i * WORDS;
        uint8x16_t v = vdupq_n_u8(0);
        for (int w = 0; w < WORDS; w += 2) {
            uint64x2_t t = vld1q_u64(tp + w);
            uint64x2_t s = vld1q_u64(Qs + w);
            uint64x2_t m = vld1q_u64(Qm + w);
            uint64x2_t x = vandq_u64(veorq_u64(t, s), m);
            v = vaddq_u8(v, vcntq_u8(vreinterpretq_u8_u64(x)));
        }
        scores[i] = 2 * Qnnz - 4 * (int32_t)vaddlvq_u8(v);
    }
}

typedef struct { int id; int cpu; } warg;

static void *worker(void *a) {
    warg *w = (warg *)a;
    cpu_set_t set; CPU_ZERO(&set); CPU_SET(w->cpu, &set);
    sched_setaffinity(0, sizeof set, &set);
    int seen = 0;
    for (;;) {
        while (atomic_load_explicit(&b_gen, memory_order_acquire) == seen) {
            if (atomic_load_explicit(&b_stop, memory_order_relaxed)) return NULL;
        }
        seen = atomic_load_explicit(&b_gen, memory_order_acquire);
        if (!atomic_load_explicit(&b_empty, memory_order_relaxed)) {
            if (atomic_load_explicit(&b_dyn, memory_order_relaxed)) {
                for (;;) {   /* work stealing: claim CHUNK rows at a time */
                    long lo = atomic_fetch_add_explicit(&b_cursor, CHUNK,
                                                        memory_order_relaxed);
                    if (lo >= NROWS) break;
                    long hi = lo + CHUNK > NROWS ? NROWS : lo + CHUNK;
                    kernel_rows(lo, hi);
                }
            } else {         /* static: equal contiguous chunks */
                long c = (NROWS + b_nthreads - 1) / b_nthreads;
                long lo = (long)w->id * c;
                long hi = lo + c > NROWS ? NROWS : lo + c;
                if (lo < NROWS) kernel_rows(lo, hi);
            }
        }
        atomic_fetch_sub_explicit(&b_left, 1, memory_order_release);
    }
}

static void dispatch(void) {
    atomic_store_explicit(&b_cursor, 0, memory_order_relaxed);
    atomic_store_explicit(&b_left, b_nthreads, memory_order_relaxed);
    atomic_fetch_add_explicit(&b_gen, 1, memory_order_release);
    while (atomic_load_explicit(&b_left, memory_order_acquire) > 0) { }
}

static uint64_t digest(void) {
    uint64_t h = 1469598103934665603ull;
    for (long i = 0; i < NROWS; i++) {
        h ^= (uint64_t)(uint32_t)scores[i];
        h *= 1099511628211ull;
    }
    return h;
}

static long cur_khz(int cpu) {
    char p[128]; snprintf(p, sizeof p,
        "/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq", cpu);
    FILE *f = fopen(p, "r"); if (!f) return -1;
    long v = -1; if (fscanf(f, "%ld", &v) != 1) v = -1; fclose(f); return v;
}

static int cmp_d(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

/* order matters on a heterogeneous part: fill the prime cores LAST so the
 * 1..6 thread points are apples to apples on performance cores */
static const int CPUORDER[MAXT] = {0, 1, 2, 3, 4, 5, 6, 7};

static double measure(int nt, int dyn, int empty, uint64_t *dg) {
    b_nthreads = nt;
    atomic_store(&b_dyn, dyn);
    atomic_store(&b_empty, empty);
    pthread_t th[MAXT]; warg wa[MAXT];
    atomic_store(&b_gen, 0); atomic_store(&b_stop, 0);
    atomic_store(&b_left, 0);
    for (int i = 0; i < nt; i++) {
        wa[i].id = i; wa[i].cpu = CPUORDER[i];
        pthread_create(&th[i], NULL, worker, &wa[i]);
    }
    struct timespec ts = {0, 50000000L}; nanosleep(&ts, NULL);  /* let them spin up */

    /* amortise: enough passes that dispatch overhead cannot dominate */
    long inner = empty ? 2000 : 20;
    double s[REPS];
    for (int k = 0; k < REPS; k++) {
        double t0 = now_s();
        for (long i = 0; i < inner; i++) dispatch();
        s[k] = (now_s() - t0) / (double)inner;
    }
    if (dg) *dg = digest();
    atomic_store(&b_stop, 1);
    atomic_fetch_add(&b_gen, 1);
    for (int i = 0; i < nt; i++) pthread_join(th[i], NULL);
    qsort(s, REPS, sizeof(double), cmp_d);
    return s[REPS / 2];
}

int main(void) {
    Tp = malloc((size_t)NROWS * WORDS * 8);
    scores = malloc((size_t)NROWS * 4);
    if (!Tp || !scores) return 1;
    for (size_t i = 0; i < (size_t)NROWS * WORDS; i++) Tp[i] = r64();
    for (int w = 0; w < WORDS; w++) {
        Qm[w] = r64(); Qs[w] = r64() & Qm[w];
        Qnnz += __builtin_popcountll(Qm[w]);
    }
    double bytes = (double)NROWS * WORDS * 8;

    printf("PAD=%d  off(left)=%zu off(cursor)=%zu  same64=%s\n", PAD,
           offsetof(bstate_t,left), offsetof(bstate_t,cursor),
           (offsetof(bstate_t,cursor)/64 == offsetof(bstate_t,left)/64)
             ? "YES (false sharing)" : "no (padded)");
    printf("S51 multi-core, spin barrier + pinned threads, %.1f MB store\n",
           bytes / 1e6);
    printf("cpu order %d%d%d%d%d%d%d%d  (perf cores first, prime 6-7 last)\n\n",
           CPUORDER[0],CPUORDER[1],CPUORDER[2],CPUORDER[3],
           CPUORDER[4],CPUORDER[5],CPUORDER[6],CPUORDER[7]);
    printf("%3s %11s %9s %9s %11s %9s %9s   %s\n",
           "T", "static_us", "GB/s", "scaling", "dynamic_us", "GB/s", "scaling",
           "barrier_us / digest");

    uint64_t d0 = 0; double base_s = 0, base_d = 0;
    for (int nt = 1; nt <= MAXT; nt++) {
        uint64_t ds = 0, dd = 0;
        double bar = measure(nt, 0, 1, NULL);
        double st  = measure(nt, 0, 0, &ds);
        double dy  = measure(nt, 1, 0, &dd);
        if (nt == 1) { base_s = st; base_d = dy; d0 = ds; }
        printf("%3d %11.1f %9.1f %8.2fx %11.1f %9.1f %8.2fx   %6.1f %s\n",
               nt, st * 1e6, bytes / st / 1e9, base_s / st,
               dy * 1e6, bytes / dy / 1e9, base_d / dy,
               bar * 1e6,
               (ds == d0 && dd == d0) ? "digest OK" : "DIGEST DIFFERS!");
    }
    printf("\nclocks after run: ");
    for (int i = 0; i < MAXT; i++) printf("cpu%d=%ldMHz ", i, cur_khz(i) / 1000);
    printf("\nbarrier column is the same dispatch with an EMPTY kernel: the null.\n");
    return 0;
}
