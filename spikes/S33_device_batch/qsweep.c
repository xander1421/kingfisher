/* S33 — does S18's batch inversion hold on the PHONE?
 *
 * S18 measured the pre-filter's arithmetic intensity on "laptop CPU via
 * Accelerate" and concluded: q=1 is bandwidth-bound at 7.3 GOP/s, q=256 hits
 * 1032 GOP/s, you pay to stream the shard once and every query after is
 * nearly free. The custody/tier architecture is built on that line.
 *
 * The ARGUMENT is architecture-independent: intensity is 2*q ops/byte
 * regardless of machine. The CROSSOVER is not. An M4 Pro has roughly 3.5x the
 * memory bandwidth of an SM8750 and a very different cache hierarchy, so the
 * q at which the phone stops being bandwidth-bound, and the marginal cost of
 * query number two, must be measured on the phone.
 *
 * Same kernel at every q, so the SHAPE of the curve is valid even though this
 * hand-written kernel will not reach the machine's peak the way Accelerate
 * does on the laptop. The shape is what the architecture rests on.
 *
 * Reports cold and warm separately (S9's rule) and repeats to expose the
 * sustained/burst gap S30 found.
 *
 * Build: aarch64-linux-android29-clang -O3 -o qsweep qsweep.c
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define D 1024
#define NROWS 100000            /* 100k triples, S5's store size */
#define REPS 5

static int8_t *T;               /* NROWS x D, the shard */
static int8_t *Q;               /* qmax x D */
static int32_t *out;

static double now_s(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* The pre-filter: scores[q][row] = dot(Q[q], T[row]).
 * Straightforward loop; -O3 will use SDOT/NEON where it can. The point is
 * that the SAME code runs at every q, so the curve is comparable. */
static void prefilter(int q) {
    for (int r = 0; r < NROWS; r++) {
        const int8_t *row = T + (size_t)r * D;
        for (int j = 0; j < q; j++) {
            const int8_t *qq = Q + (size_t)j * D;
            int32_t acc = 0;
            for (int i = 0; i < D; i++) acc += (int32_t)row[i] * (int32_t)qq[i];
            out[(size_t)j * NROWS + r] = acc;
        }
    }
}

int main(int argc, char **argv) {
    int qs[] = {1, 4, 16, 64, 100, 256};
    int nq = (int)(sizeof qs / sizeof qs[0]);
    int qmax = qs[nq - 1];

    T = malloc((size_t)NROWS * D);
    Q = malloc((size_t)qmax * D);
    out = malloc((size_t)qmax * NROWS * sizeof(int32_t));
    if (!T || !Q || !out) { fprintf(stderr, "alloc failed\n"); return 1; }

    uint32_t s = 0xC0FFEE;
#define NEXT() (s ^= s << 13, s ^= s >> 17, s ^= s << 5, s)
    for (size_t i = 0; i < (size_t)NROWS * D; i++) T[i] = (NEXT() & 1) ? 1 : -1;
    for (size_t i = 0; i < (size_t)qmax * D; i++) {
        uint32_t r = NEXT();
        Q[i] = (r & 2) ? 0 : ((r & 1) ? 2 : -2);   /* the real query shape */
    }
#undef NEXT

    double shard_mb = (double)NROWS * D / 1e6;
    printf("S33 device batch sweep   D=%d rows=%d  shard %.1f MB int8\n",
           D, NROWS, shard_mb);
    printf("same kernel at every q; cold and warm reported separately\n\n");
    printf("%6s %11s %10s %11s %10s %11s %12s\n",
           "q", "intensity", "cold_ms", "warm_med_ms", "GOP/s", "ms/query", "marginal_ms");

    double prev_ms = 0.0;
    for (int k = 0; k < nq; k++) {
        int q = qs[k];
        double t[REPS];
        for (int r = 0; r < REPS; r++) {
            double t0 = now_s();
            prefilter(q);
            t[r] = (now_s() - t0) * 1e3;
        }
        /* median of the warm samples (skip the first) */
        double w[REPS - 1];
        memcpy(w, t + 1, sizeof w);
        for (int a = 0; a < REPS - 2; a++)
            for (int b = a + 1; b < REPS - 1; b++)
                if (w[b] < w[a]) { double tmp = w[a]; w[a] = w[b]; w[b] = tmp; }
        double med = w[(REPS - 1) / 2];

        double ops = 2.0 * q * NROWS * D;
        double gops = ops / (med / 1e3) / 1e9;
        double marginal = (k == 0) ? med : (med - prev_ms) / (q - qs[k - 1]);
        printf("%6d %9d o/B %10.1f %11.1f %10.1f %11.3f %12.4f\n",
               q, 2 * q, t[0], med, gops, med / q, marginal);
        prev_ms = med;
    }

    printf("\nmarginal_ms = extra wall-clock per ADDITIONAL query beyond the\n"
           "previous q. If custody is the right unit, this collapses toward 0.\n");
    return 0;
}
