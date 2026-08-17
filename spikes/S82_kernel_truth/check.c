/* S82 — is the prefilter kernel CORRECT, not merely repeatable?
 * ATTACKER-1, 2026-08-17.
 *
 * out/LEDGER.md carries an open finding against "determinism across core
 * types": `S52_attack_s50` scored *"digest proves repeatability, not
 * correctness; the kernel was rewritten for S50 so a regression would be
 * invisible. Fix = one assertion: S45's 12-row ground truth through the new
 * kernel."*  Another falsifier written down and left unrun.
 *
 * TWO THINGS THIS RUNS, and the second is the one that matters:
 *
 * 1. NEON vs SCALAR, every row. S45 checked 12 shortlist rows against ground
 *    truth; S50 checks a digest against itself. Neither ever compared the
 *    vector kernel to an independent implementation of the same arithmetic, so
 *    a wrong-but-stable kernel would have produced exactly the evidence both
 *    spikes reported. A digest is agreement with yourself.
 *
 * 2. WHERE THE u8 ACCUMULATOR OVERFLOWS. `vsum` is a uint8x16_t summing
 *    `vcntq_u8` results across the whole word loop, and nothing in either file
 *    bounds it. Each lane takes up to 8 per iteration over WORDS/2 iterations,
 *    so the ceiling is 4*WORDS and the lane saturates past 255. At the shipped
 *    D=1024 that is 64, and there is no bug. The point is that D is a DESIGN
 *    PARAMETER, the guard does not exist, and the failure is silent and
 *    identical on every machine -- byte-identical wrong answers, which is the
 *    one failure the whole replication wedge cannot see.
 *
 * The scalar reference is the ground truth here, so it is written to be
 * obviously right rather than fast: one popcount per word, no intrinsics.
 *
 * build: cc -O2 -Wall -Wextra -Werror -o check check.c
 * run:   ./check            (sweeps D)
 */
#include <arm_neon.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Same sequenced xorshift as remeasure.c: one update per statement, so the
 * stream is defined and portable rather than depending on evaluation order.
 * Nine unsequenced-UB warnings once sat unread in files claiming bit-exactness. */
static uint32_t rng_s;
static uint32_t r32(void) {
    rng_s ^= rng_s << 13;
    rng_s ^= rng_s >> 17;
    rng_s ^= rng_s << 5;
    return rng_s;
}
static uint64_t r64(void) {
    uint64_t hi = r32();
    uint64_t lo = r32();
    return (hi << 32) | lo;
}

/* THE SHIPPED KERNEL, copied verbatim from S50 remeasure.c:44-58, which is
 * itself identical to S45 prefilter.c:105-117 apart from the accumulator's
 * name. Copied rather than paraphrased: a paraphrase would be testing my
 * transcription. */
static int32_t kernel_neon(const uint64_t *tp, const uint64_t *Qs,
                           const uint64_t *Qm, int words, int32_t Qnnz) {
    uint8x16_t v = vdupq_n_u8(0);
    for (int w = 0; w < words; w += 2) {
        uint64x2_t t = vld1q_u64(tp + w);
        uint64x2_t s = vld1q_u64(Qs + w);
        uint64x2_t m = vld1q_u64(Qm + w);
        uint64x2_t x = vandq_u64(veorq_u64(t, s), m);
        v = vaddq_u8(v, vcntq_u8(vreinterpretq_u8_u64(x)));
    }
    return 2 * Qnnz - 4 * (int32_t)vaddlvq_u8(v);
}

/* INDEPENDENT REFERENCE. Same arithmetic, no vector types, no saturation
 * surface. score = 2*Qnnz - 4*disagreements-within-mask. */
static int32_t kernel_scalar(const uint64_t *tp, const uint64_t *Qs,
                             const uint64_t *Qm, int words, int32_t Qnnz) {
    int32_t dis = 0;
    for (int w = 0; w < words; w++)
        dis += __builtin_popcountll((tp[w] ^ Qs[w]) & Qm[w]);
    return 2 * Qnnz - 4 * dis;
}

/* The quantity nothing in either spike records: the largest value any single
 * u8 lane reaches. This is the headroom, and it is what turns "no bug at
 * D=1024" into a bound someone can check before changing D. */
static int max_lane(const uint64_t *tp, const uint64_t *Qs,
                    const uint64_t *Qm, int words) {
    int lane[16] = {0};
    for (int w = 0; w < words; w += 2) {
        uint64_t x[2];
        x[0] = (tp[w] ^ Qs[w]) & Qm[w];
        x[1] = (tp[w + 1] ^ Qs[w + 1]) & Qm[w + 1];
        const uint8_t *b = (const uint8_t *)x;
        for (int k = 0; k < 16; k++)
            lane[k] += __builtin_popcount(b[k]);
    }
    int m = 0;
    for (int k = 0; k < 16; k++) if (lane[k] > m) m = lane[k];
    return m;
}

static int sweep(int D, long rows, int verbose) {
    const int words = D / 64;
    uint64_t *Tp = malloc((size_t)rows * words * 8);
    uint64_t *Qs = calloc((size_t)words, 8);
    uint64_t *Qm = calloc((size_t)words, 8);
    if (!Tp || !Qs || !Qm) { fprintf(stderr, "alloc\n"); exit(1); }

    rng_s = 0xC0FFEE;                                  /* PINNED SEED */
    for (size_t i = 0; i < (size_t)rows * words; i++) Tp[i] = r64();
    int32_t Qnnz = 0;
    for (int w = 0; w < words; w++) {                  /* as remeasure.c does */
        Qm[w] = r64();
        Qs[w] = r64() & Qm[w];
        Qnnz += __builtin_popcountll(Qm[w]);
    }

    long mismatch = 0; int worst_lane = 0; long first_bad = -1;
    int32_t got = 0, want = 0;
    for (long i = 0; i < rows; i++) {
        const uint64_t *tp = Tp + (size_t)i * words;
        int32_t a = kernel_neon(tp, Qs, Qm, words, Qnnz);
        int32_t b = kernel_scalar(tp, Qs, Qm, words, Qnnz);
        int L = max_lane(tp, Qs, Qm, words);
        if (L > worst_lane) worst_lane = L;
        if (a != b) {
            if (first_bad < 0) { first_bad = i; got = a; want = b; }
            mismatch++;
        }
    }
    printf("  D=%-6d words=%-4d rows=%-7ld Qnnz=%-5d  max u8 lane %3d/255  "
           "mismatch %ld/%ld", D, words, rows, Qnnz, worst_lane, mismatch, rows);
    if (mismatch) printf("   FIRST row %ld: neon %d, scalar %d", first_bad, got, want);
    printf("\n");
    if (verbose && mismatch)
        printf("      -> the u8 lane saturated; the kernel is WRONG here, "
               "silently, and identically on every machine\n");
    free(Tp); free(Qs); free(Qm);
    return mismatch != 0;
}

int main(void) {
    printf("S82 — NEON prefilter kernel vs an independent scalar reference\n");
    printf("kernel copied verbatim from S50 remeasure.c:44-58 "
           "(= S45 prefilter.c:105-117)\n\n");

    printf("SHIPPED CONFIGURATION\n");
    int bad_shipped = sweep(1024, 100000, 1);

    printf("\nD SWEEP — D is a design parameter and nothing guards it\n");
    int first_break = 0;
    for (int D = 1024; D <= 32768; D *= 2) {
        if (sweep(D, 2000, 0) && !first_break) first_break = D;
    }

    printf("\n");
    if (bad_shipped) {
        printf("VERDICT: the SHIPPED kernel disagrees with the reference.\n");
        return 1;
    }
    printf("VERDICT: at the shipped D=1024 the kernel is correct on every row "
           "(100000/100000),\n         not merely repeatable. ");
    if (first_break)
        printf("It breaks at D=%d and above.\n", first_break);
    else
        printf("No break found up to D=32768.\n");
    return 0;
}
