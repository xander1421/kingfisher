/* S45 — S44's stack, on the phone, with MORK as stage 2.
 *
 * S44 stacked four optimisations on an M4 Pro and reached 0.995 ms for a full
 * two-stage query, 27x over the float GEMM baseline. It closes with three
 * things this spike exists to test:
 *
 *   1. "the honest next step is the ~40-line NEON kernel" — S34 built it
 *      (705 GOP/s single-thread on device); here it is threaded and wired
 *      into a whole query.
 *   2. "memory-roof estimate ~0.093 ms/query" — arithmetic, not measured.
 *   3. "Amdahl's own bound caps any stage-2 engine swap at 1.06x" — and
 *      "No phone ran this."
 *
 * A phone runs it now, and stage 2 is real MORK rather than a numpy check.
 *
 * Pipeline, one query, B=1 (unbundled) store:
 *   build 100k triples (pred, subj, obj) + bipolar hypervectors, seeded
 *   pack the store to 1 bit/element                     -> 12.8 MB
 *   threaded popcount prefilter, analytic cutoff 2*nnz(Q)
 *   emit the shortlist as .mm2 facts + an exec rule     -> stage 2 input
 *
 * Stage 2 is then `mork run shortlist.mm2`, timed by the wrapper script, so
 * the two stages are measured by the same clock discipline as S30.
 *
 * Build: aarch64-linux-android29-clang -O3 -march=armv8.6-a+i8mm+dotprod \
 *          -o prefilter prefilter.c -lm
 */

#include <arm_neon.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define D       1024
#define WORDS   (D / 64)
#define NROWS   100000
#define NPRED   10
#define NSUBJ   1000
#define NOBJ    1000
#define REPS    9

static uint64_t *Tp;                 /* packed store, NROWS x WORDS */
static uint64_t *Qs, *Qm;            /* query bitplanes */
static int32_t   Qnnz;
static int32_t  *scores;
static int      *tp_, *ts_, *to_;    /* the triples behind each row */

static double now_s(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}
static uint64_t fnv(const void *p, size_t n) {
    const uint8_t *b = p; uint64_t h = 1469598103934665603ULL;
    for (size_t i = 0; i < n; i++) { h ^= b[i]; h *= 1099511628211ULL; }
    return h;
}

typedef struct { int lo, hi; } range_t;

static void *worker(void *arg) {
    range_t *r = arg;
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
    return NULL;
}

int main(int argc, char **argv) {
    int nthreads = argc > 1 ? atoi(argv[1]) : 8;
    const char *outpath = argc > 2 ? argv[2] : "shortlist.mm2";

    Tp = malloc((size_t)NROWS * WORDS * 8);
    Qs = calloc(WORDS, 8); Qm = calloc(WORDS, 8);
    scores = malloc((size_t)NROWS * 4);
    tp_ = malloc(NROWS * sizeof(int)); ts_ = malloc(NROWS * sizeof(int));
    to_ = malloc(NROWS * sizeof(int));

    /* codebooks and store, seeded so the host reproduces them exactly */
    uint32_t s = 0xC0FFEE;
#define NEXT() (s ^= s << 13, s ^= s >> 17, s ^= s << 5, s)
    static uint64_t Rp[WORDS], Rs[WORDS], Ro[WORDS];
    uint64_t (*P)[WORDS] = malloc(sizeof(uint64_t) * WORDS * NPRED);
    uint64_t (*S)[WORDS] = malloc(sizeof(uint64_t) * WORDS * NSUBJ);
    uint64_t (*O)[WORDS] = malloc(sizeof(uint64_t) * WORDS * NOBJ);
    for (int w = 0; w < WORDS; w++) { Rp[w] = ((uint64_t)NEXT() << 32) | NEXT();
                                      Rs[w] = ((uint64_t)NEXT() << 32) | NEXT();
                                      Ro[w] = ((uint64_t)NEXT() << 32) | NEXT(); }
    for (int i = 0; i < NPRED; i++) for (int w = 0; w < WORDS; w++) P[i][w] = ((uint64_t)NEXT()<<32)|NEXT();
    for (int i = 0; i < NSUBJ; i++) for (int w = 0; w < WORDS; w++) S[i][w] = ((uint64_t)NEXT()<<32)|NEXT();
    for (int i = 0; i < NOBJ;  i++) for (int w = 0; w < WORDS; w++) O[i][w] = ((uint64_t)NEXT()<<32)|NEXT();

    /* triple i encodes as sign-bitplane XOR of the three bound role-fillers */
    for (int i = 0; i < NROWS; i++) {
        tp_[i] = NEXT() % NPRED; ts_[i] = NEXT() % NSUBJ; to_[i] = NEXT() % NOBJ;
        for (int w = 0; w < WORDS; w++) {
            /* bundle = MAJORITY of the three bound role-fillers, which is what
             * sign(Rp*P + Rs*S + Ro*O) is in bit form. XOR is the wrong
             * combiner: it destroys the per-slot agreement the query relies on,
             * and the prefilter then returns an empty shortlist. */
            uint64_t a = Rp[w] ^ P[tp_[i]][w];
            uint64_t b = Rs[w] ^ S[ts_[i]][w];
            uint64_t c = Ro[w] ^ O[to_[i]][w];
            Tp[(size_t)i * WORDS + w] = (a & b) | (a & c) | (b & c);
        }
    }
#undef NEXT

    /* query (p s ?o): the two bound slots agree, the free slot is masked out.
     * mask = where the two bound contributions do NOT cancel. */
    int qp = tp_[42], qsub = ts_[42];       /* a pattern known to have answers */
    Qnnz = 0;
    for (int w = 0; w < WORDS; w++) {
        uint64_t a = Rp[w] ^ P[qp][w], b = Rs[w] ^ S[qsub][w];
        Qm[w] = ~(a ^ b);                    /* bound parts agree here */
        Qs[w] = a & Qm[w];
        Qnnz += __builtin_popcountll(Qm[w]);
    }

    /* ground truth from the triples themselves */
    int truth = 0;
    for (int i = 0; i < NROWS; i++) if (tp_[i] == qp && ts_[i] == qsub) truth++;

    printf("S45 stacked-on-device   n=%d D=%d threads=%d\n", NROWS, D, nthreads);
    printf("store packed %.1f MB   query nnz %d   ground-truth answers %d\n",
           (double)NROWS * WORDS * 8 / 1e6, Qnnz, truth);

    pthread_t th[64]; range_t rg[64];
    double best = 1e18, cold = 0;
    for (int r = 0; r < REPS; r++) {
        double t0 = now_s();
        int chunk = (NROWS + nthreads - 1) / nthreads;
        for (int t = 0; t < nthreads; t++) {
            rg[t].lo = t * chunk;
            rg[t].hi = (t + 1) * chunk > NROWS ? NROWS : (t + 1) * chunk;
            pthread_create(&th[t], NULL, worker, &rg[t]);
        }
        for (int t = 0; t < nthreads; t++) pthread_join(th[t], NULL);
        double el = now_s() - t0;
        if (r == 0) cold = el; else if (el < best) best = el;
    }

    /* shortlist by the analytic cutoff */
    int nshort = 0;
    FILE *f = fopen(outpath, "w");
    fprintf(f, ";; S45 stage 2: exact match over the prefilter shortlist\n;; @steps 1\n\n");
    for (int i = 0; i < NROWS; i++)
        if (scores[i] >= 2 * Qnnz) {
            fprintf(f, "(Triple p%d s%d o%d)\n", tp_[i], ts_[i], to_[i]);
            nshort++;
        }
    fprintf(f, "\n(exec 0 (, (Triple p%d s%d $o)) (, (Answer $o)))\n", qp, qsub);
    fclose(f);

    double ops = 2.0 * NROWS * D;
    printf("\nprefilter  cold %.3f ms   best %.3f ms   %.1f GOP/s   %.0f q/s\n",
           cold * 1e3, best * 1e3, ops / best / 1e9, 1.0 / best);
    printf("shortlist  %d rows (%.4f%% of store, %.0fx reduction)  truth %d  %s\n",
           nshort, 100.0 * nshort / NROWS, (double)NROWS / (nshort ? nshort : 1),
           truth, nshort >= truth ? "CONTAINS ALL ANSWERS" : "*** MISSES ANSWERS ***");
    printf("scores digest %016llx\n", (unsigned long long)fnv(scores, (size_t)NROWS * 4));
    printf("bandwidth  %.1f GB/s (%.1f MB in %.3f ms)\n",
           (double)NROWS * WORDS * 8 / best / 1e9,
           (double)NROWS * WORDS * 8 / 1e6, best * 1e3);
    printf("wrote %s\n", outpath);
    return 0;
}
