/* S34 — N1 + N4: can a packed popcount kernel close the 17x gap, and does it
 * produce the identical int32 the CPU reference produces, on two machines?
 *
 * S33 measured the naive int8 kernel at 50.7 GOP/s on the phone and showed the
 * phone needs ~5.0 TOP/s to be bandwidth-bound at q=100 — a 17x shortfall that
 * the whole custody/tier architecture depends on closing.
 *
 * Three kernels, identical outputs required:
 *   K0  scalar int8 reference          — the ground truth, 1024 MACs/row
 *   K1  NEON SDOT int8                 — vdotq_s32, 4 MACs per lane-group
 *   K2  packed bitplane popcount       — the exactness argument
 *
 * K2's identity, for the real three-valued query Q in {-2,0,+2} against a
 * bipolar store T in {-1,+1}:
 *
 *     score = sum_d Q_d * T_d
 *           = 2 * [ #agree - #disagree ]        over d where Q_d != 0
 *           = 2*nnz(Q) - 4*popcount(mask & (sign_q XOR sign_t))
 *
 * so one XOR, one AND and one popcount per 64 bits replaces 64 MACs, and the
 * store shrinks 8x (1 bit/element instead of int8). No quantisation, no scale,
 * no accumulator width to negotiate: a popcount is a popcount on any silicon.
 * That is why this is the only NPU-legal form under a byte-comparison network.
 *
 * N4: every kernel's full int32 score array is hashed (FNV-1a, deterministic)
 * and printed, so the phone and the host can be compared byte for byte.
 *
 * Build (both targets — the host is also arm64):
 *   aarch64-linux-android29-clang -O3 -march=armv8.6-a+i8mm+dotprod -o kernels kernels.c
 *   clang -O3 -o kernels_host kernels.c
 */

#include <arm_neon.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define D      1024
#define WORDS  (D / 64)          /* 16 u64 words per packed row */
#define NROWS  100000
#define REPS   5

static int8_t   *T8;             /* NROWS x D int8, bipolar +-1 */
static uint64_t *Tp;             /* NROWS x WORDS packed sign bits (1 = -1) */
static int8_t   *Q8;             /* qmax x D, values in {-2,0,+2} */
static uint64_t *Qsign, *Qmask;  /* qmax x WORDS bitplanes */
static int32_t  *Qnnz;
static int32_t  *out0, *out1, *out2;

static double now_s(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static uint64_t fnv(const void *p, size_t n) {
    const uint8_t *b = p; uint64_t h = 1469598103934665603ULL;
    for (size_t i = 0; i < n; i++) { h ^= b[i]; h *= 1099511628211ULL; }
    return h;
}

/* ---------------------------------------------------------------- K0 */
static void k0_scalar(int q) {
    for (int j = 0; j < q; j++) {
        const int8_t *qq = Q8 + (size_t)j * D;
        for (int r = 0; r < NROWS; r++) {
            const int8_t *row = T8 + (size_t)r * D;
            int32_t acc = 0;
            for (int i = 0; i < D; i++) acc += (int32_t)row[i] * (int32_t)qq[i];
            out0[(size_t)j * NROWS + r] = acc;
        }
    }
}

/* ---------------------------------------------------------------- K1 */
static void k1_sdot(int q) {
    for (int j = 0; j < q; j++) {
        const int8_t *qq = Q8 + (size_t)j * D;
        for (int r = 0; r < NROWS; r++) {
            const int8_t *row = T8 + (size_t)r * D;
            int32x4_t acc = vdupq_n_s32(0);
            for (int i = 0; i < D; i += 16) {
                int8x16_t a = vld1q_s8(row + i);
                int8x16_t b = vld1q_s8(qq + i);
                acc = vdotq_s32(acc, a, b);
            }
            out1[(size_t)j * NROWS + r] = vaddvq_s32(acc);
        }
    }
}

/* ---------------------------------------------------------------- K2 */
static void k2_popcount(int q) {
    for (int j = 0; j < q; j++) {
        const uint64_t *qs = Qsign + (size_t)j * WORDS;
        const uint64_t *qm = Qmask + (size_t)j * WORDS;
        const int32_t nnz = Qnnz[j];
        for (int r = 0; r < NROWS; r++) {
            const uint64_t *tp = Tp + (size_t)r * WORDS;
            uint8x16_t vsum = vdupq_n_u8(0);
            for (int w = 0; w < WORDS; w += 2) {
                uint64x2_t t = vld1q_u64(tp + w);
                uint64x2_t s = vld1q_u64(qs + w);
                uint64x2_t m = vld1q_u64(qm + w);
                uint64x2_t x = vandq_u64(veorq_u64(t, s), m);
                vsum = vaddq_u8(vsum, vcntq_u8(vreinterpretq_u8_u64(x)));
            }
            int32_t dis = (int32_t)vaddlvq_u8(vsum);
            out2[(size_t)j * NROWS + r] = 2 * nnz - 4 * dis;
        }
    }
}

int main(void) {
    int qs[] = {1, 4, 16, 64, 100, 256};
    int nq = (int)(sizeof qs / sizeof qs[0]), qmax = qs[nq - 1];

    T8 = malloc((size_t)NROWS * D);
    Tp = malloc((size_t)NROWS * WORDS * 8);
    Q8 = malloc((size_t)qmax * D);
    Qsign = calloc((size_t)qmax * WORDS, 8);
    Qmask = calloc((size_t)qmax * WORDS, 8);
    Qnnz = calloc(qmax, sizeof(int32_t));
    out0 = malloc((size_t)qmax * NROWS * 4);
    out1 = malloc((size_t)qmax * NROWS * 4);
    out2 = malloc((size_t)qmax * NROWS * 4);
    if (!T8 || !Tp || !out0 || !out1 || !out2) { fprintf(stderr,"alloc\n"); return 1; }

    uint32_t s = 0xC0FFEE;
#define NEXT() (s ^= s << 13, s ^= s >> 17, s ^= s << 5, s)
    for (size_t i = 0; i < (size_t)NROWS * D; i++) T8[i] = (NEXT() & 1) ? 1 : -1;
    for (size_t i = 0; i < (size_t)qmax * D; i++) {
        uint32_t r = NEXT();
        Q8[i] = (r & 2) ? 0 : ((r & 1) ? 2 : -2);
    }
#undef NEXT
    /* pack: bit set == value is negative */
    memset(Tp, 0, (size_t)NROWS * WORDS * 8);
    for (int r = 0; r < NROWS; r++)
        for (int i = 0; i < D; i++)
            if (T8[(size_t)r * D + i] < 0)
                Tp[(size_t)r * WORDS + i / 64] |= 1ULL << (i % 64);
    for (int j = 0; j < qmax; j++)
        for (int i = 0; i < D; i++) {
            int8_t v = Q8[(size_t)j * D + i];
            if (v != 0) {
                Qmask[(size_t)j * WORDS + i / 64] |= 1ULL << (i % 64);
                Qnnz[j]++;
                if (v < 0) Qsign[(size_t)j * WORDS + i / 64] |= 1ULL << (i % 64);
            }
        }

    printf("S34 packed popcount   D=%d rows=%d\n", D, NROWS);
    printf("store: int8 %.1f MB   packed %.1f MB (%.0fx smaller)\n\n",
           (double)NROWS * D / 1e6, (double)NROWS * WORDS * 8 / 1e6,
           (double)D / (WORDS * 8.0));

    /* ---- exactness first. Speed is meaningless if the answers differ. ---- */
    k0_scalar(4); k1_sdot(4); k2_popcount(4);
    size_t nb = (size_t)4 * NROWS * 4;
    int ok01 = memcmp(out0, out1, nb) == 0;
    int ok02 = memcmp(out0, out2, nb) == 0;
    printf("EXACTNESS (q=4, %d rows)\n", NROWS);
    printf("  K0 scalar   fnv %016llx\n", (unsigned long long)fnv(out0, nb));
    printf("  K1 SDOT     fnv %016llx  %s\n", (unsigned long long)fnv(out1, nb),
           ok01 ? "IDENTICAL to K0" : "*** DIFFERS ***");
    printf("  K2 popcount fnv %016llx  %s\n", (unsigned long long)fnv(out2, nb),
           ok02 ? "IDENTICAL to K0" : "*** DIFFERS ***");
    if (!ok01 || !ok02) { printf("\nabort: kernels disagree\n"); return 1; }

    /* ---- speed ---- */
    printf("\n%6s %10s %10s %10s %9s %9s %9s\n",
           "q", "K0_ms", "K1_ms", "K2_ms", "K0_GOP/s", "K1_GOP/s", "K2_GOP/s");
    for (int k = 0; k < nq; k++) {
        int q = qs[k];
        double best[3] = {1e18, 1e18, 1e18};
        for (int r = 0; r < REPS; r++) {
            double t0 = now_s(); k0_scalar(q);   double a = now_s() - t0;
            t0 = now_s();       k1_sdot(q);      double b = now_s() - t0;
            t0 = now_s();       k2_popcount(q);  double c = now_s() - t0;
            if (r) { /* skip the cold rep */
                if (a < best[0]) best[0] = a;
                if (b < best[1]) best[1] = b;
                if (c < best[2]) best[2] = c;
            }
        }
        double ops = 2.0 * q * NROWS * D;
        printf("%6d %10.1f %10.1f %10.1f %9.1f %9.1f %9.1f\n",
               q, best[0]*1e3, best[1]*1e3, best[2]*1e3,
               ops/best[0]/1e9, ops/best[1]/1e9, ops/best[2]/1e9);
        if (q == 100) {
            printf("       -> at q=100 the roof needs 5.0 TOP/s; K2 reaches "
                   "%.2f TOP/s (%.1fx short)\n",
                   ops/best[2]/1e12, 5.0e12/(ops/best[2]));
        }
    }

    /* ---- N4: full-array digests for cross-device comparison ---- */
    k2_popcount(100);
    printf("\nN4 cross-device digest, q=100 full score array:\n");
    printf("  K2 fnv %016llx  (%zu bytes)\n",
           (unsigned long long)fnv(out2, (size_t)100 * NROWS * 4),
           (size_t)100 * NROWS * 4);
    return 0;
}
