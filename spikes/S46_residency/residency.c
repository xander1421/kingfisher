/* S46 — what does residency actually buy? Measured with cache as the proxy
 * for VTCM.
 *
 * S45b established the chain the NPU plan depends on:
 *     bundle -> fits VTCM (8 MB) -> resident -> escapes the DRAM roof
 * and measured the roof: 58.9 GB/s read, with the prefilter at 86% of it.
 *
 * The middle of that chain is testable right now without a DSP. A bundled
 * store is small; small stores fit in cache; cache is a memory system the DRAM
 * roof does not apply to. So sweep the store size and find where the prefilter
 * stops being DRAM-bound. Whatever the speedup is at 400 KB (the B=64
 * two-bitplane size) is the upper bound on what VTCM residency can buy,
 * measured on this silicon rather than argued from a datasheet.
 *
 * Same kernel, same pool, same digest discipline as S45b. Only NROWS varies.
 *
 * Build: aarch64-linux-android29-clang -O3 -march=armv8.6-a+i8mm+dotprod \
 *          -o residency residency.c -lm
 */

#include <arm_neon.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define D      1024
#define WORDS  (D / 64)
#define MAXROWS 100000
#define REPS   15

static uint64_t *Tp, *Qs, *Qm;
static int32_t   Qnnz, *scores;
static int       g_rows, g_threads;

static double now_s(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}
static uint64_t fnv(const void *p, size_t n) {
    const uint8_t *b = p; uint64_t h = 1469598103934665603ULL;
    for (size_t i = 0; i < n; i++) { h ^= b[i]; h *= 1099511628211ULL; }
    return h;
}

typedef struct { int lo, hi; } range_t;
static pthread_mutex_t mx = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t  go = PTHREAD_COND_INITIALIZER, done = PTHREAD_COND_INITIALIZER;
static int gen = 0, busy = 0, stop = 0;
static range_t rg[64];

static void chunk(const range_t *r) {
    for (int i = r->lo; i < r->hi; i++) {
        const uint64_t *tp = Tp + (size_t)i * WORDS;
        uint8x16_t vsum = vdupq_n_u8(0);
        for (int w = 0; w < WORDS; w += 2) {
            uint64x2_t t = vld1q_u64(tp + w);
            uint64x2_t s = vld1q_u64(Qs + w);
            uint64x2_t m = vld1q_u64(Qm + w);
            uint64x2_t x = vandq_u64(veorq_u64(t, s), m);
            vsum = vaddq_u8(vsum, vcntq_u8(vreinterpretq_u8_u64(x)));
        }
        scores[i] = 2 * Qnnz - 4 * (int32_t)vaddlvq_u8(vsum);
    }
}

static void *w_fn(void *a) {
    int id = (int)(intptr_t)a, seen = 0;
    for (;;) {
        pthread_mutex_lock(&mx);
        while (gen == seen && !stop) pthread_cond_wait(&go, &mx);
        if (stop) { pthread_mutex_unlock(&mx); return NULL; }
        seen = gen; pthread_mutex_unlock(&mx);
        chunk(&rg[id]);
        pthread_mutex_lock(&mx);
        if (--busy == 0) pthread_cond_signal(&done);
        pthread_mutex_unlock(&mx);
    }
}
static void dispatch(void) {
    pthread_mutex_lock(&mx);
    busy = g_threads; gen++;
    pthread_cond_broadcast(&go);
    while (busy) pthread_cond_wait(&done, &mx);
    pthread_mutex_unlock(&mx);
}

int main(int argc, char **argv) {
    g_threads = argc > 1 ? atoi(argv[1]) : 4;

    Tp = malloc((size_t)MAXROWS * WORDS * 8);
    Qs = calloc(WORDS, 8); Qm = calloc(WORDS, 8);
    scores = malloc((size_t)MAXROWS * 4);

    uint32_t s = 0xC0FFEE;
#define NEXT() (s ^= s << 13, s ^= s >> 17, s ^= s << 5, s)
    for (size_t i = 0; i < (size_t)MAXROWS * WORDS; i++)
        Tp[i] = ((uint64_t)NEXT() << 32) | NEXT();
    for (int w = 0; w < WORDS; w++) {
        Qm[w] = ((uint64_t)NEXT() << 32) | NEXT();
        Qs[w] = (((uint64_t)NEXT() << 32) | NEXT()) & Qm[w];
        Qnnz += __builtin_popcountll(Qm[w]);
    }
#undef NEXT

    /* threads=0 selects the inline path. The pooled sweep showed best_us
     * flooring at ~40-75 us no matter how small the store got, which is the
     * condvar round trip, not the memory system -- the same mistake S18 made
     * with BLAS call overhead. Inline removes the barrier entirely so the
     * resident-bandwidth curve can be seen. */
    pthread_t th[64];
    for (int t = 0; t < g_threads; t++)
        pthread_create(&th[t], NULL, w_fn, (void *)(intptr_t)t);

    printf("S46 residency sweep   D=%d threads=%d   (DRAM roof measured 58.9 GB/s)\n\n",
           D, g_threads);
    printf("%9s %11s %11s %11s %10s %12s\n",
           "rows", "store_KB", "best_us", "GB/s", "q/s", "vs_12.8MB");

    int sizes[] = {100000, 50000, 25000, 12500, 6250, 3125, 1562, 780, 390, 195};
    double base_gbs = 0;
    for (int k = 0; k < (int)(sizeof sizes / sizeof sizes[0]); k++) {
        g_rows = sizes[k];
        int c = (g_rows + g_threads - 1) / g_threads;
        for (int t = 0; t < g_threads; t++) {
            rg[t].lo = t * c;
            rg[t].hi = (t + 1) * c > g_rows ? g_rows : (t + 1) * c;
        }
        double best = 1e18;
        for (int r = 0; r < REPS; r++) {
            double t0 = now_s();
            if (g_threads == 0) {            /* inline: no pool, no barrier */
                range_t all = {0, g_rows};
                chunk(&all);
            } else {
                dispatch();
            }
            double e = now_s() - t0;
            if (r && e < best) best = e;
        }
        double bytes = (double)g_rows * WORDS * 8;
        double gbs = bytes / best / 1e9;
        if (k == 0) base_gbs = gbs;
        printf("%9d %11.1f %11.1f %11.1f %10.0f %11.2fx\n",
               g_rows, bytes / 1024.0, best * 1e6, gbs, 1.0 / best, gbs / base_gbs);
    }

    printf("\ndigest(scores, 100k rows) %016llx\n",
           (unsigned long long)fnv(scores, (size_t)195 * 4));
    pthread_mutex_lock(&mx); stop = 1;
    pthread_cond_broadcast(&go); pthread_mutex_unlock(&mx);
    for (int t = 0; t < g_threads; t++) pthread_join(th[t], NULL);
    return 0;
}
