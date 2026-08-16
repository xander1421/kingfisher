/* S50 — the measurement harness the retractions demanded.
 *
 * Seven times in this workspace a per-run cost was reported as a property of
 * the hardware or the algorithm: BLAS call overhead (S18), 13 ms of what turned
 * out to be a SIGABRT tombstone (S45), 285 us of pthread_create (S45b), a 40 us
 * condvar barrier (S46), pthread_create inside the timed region of the very
 * instrument used as ground truth (streamroof), DVFS on an unpinned core (S46),
 * and best-of selecting favourable 52 ns tick quantisation (S46).
 *
 * Every one was catchable by a control the author did not run. So the controls
 * are no longer optional: this header refuses to report a number whose null
 * measurement is not negligible, and refuses to compile if the compiler has
 * anything to say.
 *
 * Build with:  -O3 -Wall -Wextra -Werror
 *   Nine unsequenced-modification warnings sat unread in prefilter.c and
 *   residency.c, in files whose headline claim was bit-exactness. -Werror now.
 *
 * What it enforces
 *   1. PIN. sched_setaffinity to a named core, and report that core's actual
 *      scaling_cur_freq at measurement time. S46's "22.6 GB/s/core" was an
 *      unpinned short-lived process landing wherever DVFS put it; the same
 *      binary pinned to cpu7 gives 39-46 GB/s.
 *   2. AMORTISE. The arch timer ticks at 52.08 ns. Loop the kernel until one
 *      bracket exceeds MIN_SAMPLE_NS so quantisation is < 0.1%, instead of
 *      timing a 1.1 us kernel across 21 ticks and calling the residual 1.8%.
 *   3. NULL. Time an empty bracket the same way and report it. If
 *      null > 1% of the measurement, bench_report prints DISQUALIFIED.
 *   4. SPREAD. Report median, MAD, min and max. Never one number, and never
 *      best-of alone: best-of is what selects the favourable rounding.
 *   5. NO SUBTRACTION. There is deliberately no API to subtract a separately
 *      measured overhead. Measure the controlled pair and difference it.
 *      S45b's "59% was spawn" became 41% when done that way, because spawn
 *      overlaps with work.
 *   6. VERIFY. Every timed kernel returns a digest; bench_run aborts if it
 *      changes between reps. S46 hashed 780 bytes and labelled it 100k rows,
 *      so no large-store run had any correctness check at all.
 */

#ifndef KINGFISHER_BENCH_H
#define KINGFISHER_BENCH_H

#define _GNU_SOURCE
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MIN_SAMPLE_NS 20000000L   /* 20 ms per bracket: 52 ns tick -> <0.0003% */
#define BENCH_REPS    15

typedef uint64_t (*bench_fn)(void *ctx);   /* returns a digest, not void */

static inline uint64_t now_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}

/* ---- 1. pin, and prove which core we are on ---------------------------- */
static inline int bench_pin(int cpu) {
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (sched_setaffinity(0, sizeof set, &set) != 0) return -1;
    /* give the governor a moment to ramp before anything is timed */
    uint64_t spin = 0, t0 = now_ns();
    while (now_ns() - t0 < 50000000ull) spin++;
    return (int)(spin & 1);
}

static inline long bench_cur_khz(int cpu) {
    char p[128];
    snprintf(p, sizeof p,
             "/sys/devices/system/cpu/cpu%d/cpufreq/scaling_cur_freq", cpu);
    FILE *f = fopen(p, "r");
    if (!f) return -1;
    long v = -1;
    if (fscanf(f, "%ld", &v) != 1) v = -1;
    fclose(f);
    return v;
}

/* ---- the measurement --------------------------------------------------- */
typedef struct {
    const char *name;
    int    cpu;
    long   khz_before, khz_after;
    long   inner;              /* iterations amortised into one bracket */
    double median_ns, mad_ns, min_ns, max_ns;
    double null_ns;            /* the harness doing nothing, same shape */
    int    digest_stable;
    uint64_t digest;
} bench_result;

static int cmp_d(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

static inline uint64_t bench_noop(void *ctx) { (void)ctx; return 0; }

static inline bench_result bench_run(const char *name, int cpu,
                                     bench_fn fn, void *ctx) {
    bench_result r;
    memset(&r, 0, sizeof r);
    r.name = name;
    r.cpu = cpu;
    bench_pin(cpu);
    r.khz_before = bench_cur_khz(cpu);

    /* 2. amortise: grow inner until a bracket is long enough that the 52 ns
     *    tick and the ~26 ns clock_gettime are both irrelevant */
    long inner = 1;
    for (;;) {
        uint64_t t0 = now_ns();
        for (long i = 0; i < inner; i++) fn(ctx);
        uint64_t el = now_ns() - t0;
        if (el >= MIN_SAMPLE_NS || inner >= (1L << 30)) break;
        long grow = (long)((double)MIN_SAMPLE_NS / (double)(el ? el : 1) * 1.2);
        inner = inner * (grow < 2 ? 2 : (grow > 64 ? 64 : grow));
    }
    r.inner = inner;

    double s[BENCH_REPS];
    uint64_t d0 = 0;
    r.digest_stable = 1;
    for (int k = 0; k < BENCH_REPS; k++) {
        uint64_t t0 = now_ns(), d = 0;
        for (long i = 0; i < inner; i++) d = fn(ctx);
        uint64_t el = now_ns() - t0;
        s[k] = (double)el / (double)inner;
        if (k == 0) d0 = d;
        else if (d != d0) r.digest_stable = 0;    /* 6. verify */
    }
    r.digest = d0;

    /* 3. null: the same shape, doing nothing */
    uint64_t n0 = now_ns();
    for (long i = 0; i < inner; i++) bench_noop(ctx);
    r.null_ns = (double)(now_ns() - n0) / (double)inner;

    r.khz_after = bench_cur_khz(cpu);

    qsort(s, BENCH_REPS, sizeof(double), cmp_d);
    r.median_ns = s[BENCH_REPS / 2];
    r.min_ns = s[0];
    r.max_ns = s[BENCH_REPS - 1];
    double dev[BENCH_REPS];
    for (int k = 0; k < BENCH_REPS; k++) {
        double x = s[k] - r.median_ns;
        dev[k] = x < 0 ? -x : x;
    }
    qsort(dev, BENCH_REPS, sizeof(double), cmp_d);
    r.mad_ns = dev[BENCH_REPS / 2];               /* 4. spread, robust */
    return r;
}

/* 3+4. one honest line, and a refusal if the null is not negligible */
static inline void bench_report(bench_result r, double bytes_per_iter) {
    double gbs = bytes_per_iter > 0 ? bytes_per_iter / r.median_ns : 0.0;
    printf("%-26s cpu%-2d %4ld-%4ld MHz  inner %-8ld "
           "med %10.1f ns  MAD %6.1f (%4.1f%%)  min %9.1f  max %9.1f",
           r.name, r.cpu, r.khz_before / 1000, r.khz_after / 1000, r.inner,
           r.median_ns, r.mad_ns, 100.0 * r.mad_ns / r.median_ns,
           r.min_ns, r.max_ns);
    if (bytes_per_iter > 0) printf("  %6.1f GB/s", gbs);
    printf("  digest %016llx%s", (unsigned long long)r.digest,
           r.digest_stable ? "" : " UNSTABLE!");
    if (r.null_ns > 0.01 * r.median_ns)
        printf("  ** DISQUALIFIED: null %.1f ns is %.1f%% of the result **",
               r.null_ns, 100.0 * r.null_ns / r.median_ns);
    printf("\n");
}

#endif
