/* S50 — re-measure the prefilter through the corrected harness.
 *
 * Replaces S45's 0.252 ms / 50.8 GB/s / "86% of the roof" / "at most 16% left
 * on the CPU", all of which died: the roof was measured with pthread_create
 * inside the timed region, at 128 MB against a 12.8 MB workload, and an
 * attacker got 2.2x more out of this same kernel by pinning and using a spin
 * barrier.
 *
 * Also fixes the undefined behaviour that -Werror now refuses to build:
 *   old: #define NEXT() (s ^= s<<13, s ^= s>>17, s ^= s<<5, s)
 *        ... ((uint64_t)NEXT()<<32)|NEXT()      <-- two updates, one expression
 * That is unsequenced modification of `s`. It never bit us — the cross-silicon
 * digests matched — but the match was two compilers agreeing by luck, while the
 * write-up claimed reproducibility by construction.
 *
 * Build: aarch64-linux-android29-clang -O3 -Wall -Wextra -Werror \
 *          -march=armv8.6-a+i8mm+dotprod -o remeasure remeasure.c
 */

#include "bench.h"
#include <arm_neon.h>

#define D      1024
#define WORDS  (D / 64)

static uint64_t *Tp, Qs[WORDS], Qm[WORDS];
static int32_t  *scores, Qnnz;
static long      g_rows;

/* sequenced: one update per statement, so the stream is defined and portable */
static uint32_t rng_s = 0xC0FFEE;
static uint32_t r32(void) {
    rng_s ^= rng_s << 13;
    rng_s ^= rng_s >> 17;
    rng_s ^= rng_s << 5;
    return rng_s;
}
static uint64_t r64(void) {
    uint64_t hi = r32();          /* two statements, defined order */
    uint64_t lo = r32();
    return (hi << 32) | lo;
}

static uint64_t prefilter(void *ctx) {
    (void)ctx;
    uint64_t acc = 1469598103934665603ull;
    for (long i = 0; i < g_rows; i++) {
        const uint64_t *tp = Tp + (size_t)i * WORDS;
        uint8x16_t v = vdupq_n_u8(0);
        for (int w = 0; w < WORDS; w += 2) {
            uint64x2_t t = vld1q_u64(tp + w);
            uint64x2_t s = vld1q_u64(Qs + w);
            uint64x2_t m = vld1q_u64(Qm + w);
            uint64x2_t x = vandq_u64(veorq_u64(t, s), m);
            v = vaddq_u8(v, vcntq_u8(vreinterpretq_u8_u64(x)));
        }
        int32_t sc = 2 * Qnnz - 4 * (int32_t)vaddlvq_u8(v);
        scores[i] = sc;
        acc = (acc ^ (uint64_t)(uint32_t)sc) * 1099511628211ull;
    }
    return acc;   /* digest over EVERY row, at every size — S46 hashed 780 B */
}

int main(int argc, char **argv) {
    (void)argv;
    long maxrows = 800000;                       /* 100 MB, past any cache */
    Tp = malloc((size_t)maxrows * WORDS * 8);
    scores = malloc((size_t)maxrows * 4);
    if (!Tp || !scores) { fprintf(stderr, "alloc\n"); return 1; }
    for (size_t i = 0; i < (size_t)maxrows * WORDS; i++) Tp[i] = r64();
    for (int w = 0; w < WORDS; w++) {
        Qm[w] = r64();
        Qs[w] = r64() & Qm[w];
        Qnnz += __builtin_popcountll(Qm[w]);
    }

    int cpus[] = {0, 7};                          /* performance, then prime */
    long sizes[] = {195, 3125, 100000, 800000};
    int ncpu = argc > 1 ? 1 : 2;

    printf("S50 remeasure — pinned, amortised, null-checked, digest-verified\n");
    printf("D=%d  query nnz=%d\n\n", D, Qnnz);

    for (int c = 0; c < ncpu; c++) {
        for (size_t k = 0; k < sizeof sizes / sizeof sizes[0]; k++) {
            g_rows = sizes[k];
            char nm[64];
            snprintf(nm, sizeof nm, "prefilter %ld rows (%.1f MB)",
                     g_rows, (double)g_rows * WORDS * 8 / 1e6);
            bench_result r = bench_run(nm, cpus[c], prefilter, NULL);
            bench_report(r, (double)g_rows * WORDS * 8);
        }
        printf("\n");
    }
    return 0;
}
