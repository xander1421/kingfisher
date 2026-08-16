/* S31 — does the phone's accelerator requantise, and can the scale be pinned?
 *
 * Answers Agent 1's C1 (chat.log). Their S12 settled two thirds of M2.1 in
 * simulation: the float32 path is integer-exact, and int16 accumulation is
 * safe. The remaining third needs silicon: an NPU backend may requantise its
 * output, and if the scale it uses cannot be pinned by the job, two honest
 * replicas disagree and the dispute mechanism fires on nothing.
 *
 * What this does:
 *   1. enumerate NNAPI devices and their types (CPU / GPU / DSP / accelerator)
 *   2. build the S5 kernel as one FULLY_CONNECTED: q (1 x D) x T^T (N x D)
 *      with QUANT8_ASYMM_SIGNED weights and input, INT32 bias
 *   3. run it TWICE with different declared output scales
 *   4. compare against an exact int32 reference computed on the CPU here
 *   5. run it pinned to each device in turn (compilation-for-device), so we
 *      learn whether the DSP/NPU and the CPU fallback agree
 *
 * The claim under test is not "is it fast" — it is "is it EXACT, and is the
 * quantisation under the job's control". Speed is printed but not the point.
 *
 * Build:
 *   $NDK/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang \
 *      -O2 -o probe probe.c -lneuralnetworks -llog
 */

#include <android/NeuralNetworks.h>
#include <android/NeuralNetworksTypes.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>

#define D 1024      /* S5's recommended operating point */
#define N 4096      /* rows of T; keep the model small enough to compile fast */
#define N_MATCH 8   /* planted matching rows */

static int8_t *T;       /* N x D  bipolar +-1, the "triples" */
static int8_t *q;       /* D      the query, values in {-2,0,2} -> see note */
static int32_t *ref;    /* N      exact int32 reference */

#define CHECK(x) do { int _e = (x); if (_e != ANEURALNETWORKS_NO_ERROR) { \
    fprintf(stderr, "%s:%d  %s -> %d\n", __FILE__, __LINE__, #x, _e); \
    return -1; } } while (0)

static double now_s(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static void make_data(unsigned seed) {
    /* xorshift so the host can reproduce the identical tensors */
    uint32_t s = seed ? seed : 1;
#define NEXT() (s ^= s << 13, s ^= s >> 17, s ^= s << 5, s)
    T = malloc((size_t)N * D);
    q = malloc(D);
    ref = malloc((size_t)N * sizeof(int32_t));
    /* The real S5 query shape: Q = R_p*P[p] + R_s*S[s], values in {-2,0,+2},
     * roughly half zeros. Matching triples score exactly 2*nnz(Q) ~ D. */
    int nnz = 0;
    for (int i = 0; i < D; i++) {
        uint32_t r = NEXT();
        q[i] = (r & 2) ? 0 : ((r & 1) ? 2 : -2);
        if (q[i]) nnz++;
    }
    for (long i = 0; i < (long)N * D; i++) T[i] = (NEXT() & 1) ? 1 : -1;
    /* plant MATCHES: rows that agree with the sign of q wherever q != 0.
     * These are the rows the pre-filter must separate, and their score is the
     * analytic cutoff 2*nnz(Q). */
    for (int m = 0; m < N_MATCH; m++) {
        int8_t *row = T + (size_t)(m * (N / N_MATCH)) * D;
        for (int i = 0; i < D; i++)
            if (q[i]) row[i] = q[i] > 0 ? 1 : -1;
    }
    printf("query nnz %d -> analytic cutoff 2*nnz(Q) = %d, %d planted matches\n",
           nnz, 2 * nnz, N_MATCH);
    for (int r = 0; r < N; r++) {
        int32_t acc = 0;
        const int8_t *row = T + (size_t)r * D;
        for (int i = 0; i < D; i++) acc += (int32_t)row[i] * (int32_t)q[i];
        ref[r] = acc;
    }
#undef NEXT
}

/* Build a model: OUT[1,N] = FULLY_CONNECTED(IN[1,D], W[N,D], BIAS[N]) */
static int build_model(ANeuralNetworksModel **out, float out_scale,
                       int32_t out_zp) {
    ANeuralNetworksModel *model;
    CHECK(ANeuralNetworksModel_create(&model));

    uint32_t in_dims[2]  = {1, D};
    uint32_t w_dims[2]   = {N, D};
    uint32_t b_dims[1]   = {N};
    uint32_t out_dims[2] = {1, N};

    /* input and weights: symmetric int8, scale 1.0, zero point 0.
     * scale 1.0 means the quantised value IS the integer value, so the
     * product is exactly the integer dot product we want. */
    ANeuralNetworksOperandType in_t = {
        .type = ANEURALNETWORKS_TENSOR_QUANT8_ASYMM_SIGNED,
        .dimensionCount = 2, .dimensions = in_dims,
        .scale = 1.0f, .zeroPoint = 0};
    ANeuralNetworksOperandType w_t = in_t; w_t.dimensions = w_dims;
    /* NNAPI requires the bias scale == input.scale * weights.scale */
    ANeuralNetworksOperandType b_t = {
        .type = ANEURALNETWORKS_TENSOR_INT32,
        .dimensionCount = 1, .dimensions = b_dims,
        .scale = 1.0f, .zeroPoint = 0};
    ANeuralNetworksOperandType out_t = {
        .type = ANEURALNETWORKS_TENSOR_QUANT8_ASYMM_SIGNED,
        .dimensionCount = 2, .dimensions = out_dims,
        .scale = out_scale, .zeroPoint = out_zp};
    ANeuralNetworksOperandType act_t = {
        .type = ANEURALNETWORKS_INT32, .dimensionCount = 0,
        .dimensions = NULL, .scale = 0.0f, .zeroPoint = 0};

    CHECK(ANeuralNetworksModel_addOperand(model, &in_t));   /* 0 */
    CHECK(ANeuralNetworksModel_addOperand(model, &w_t));    /* 1 */
    CHECK(ANeuralNetworksModel_addOperand(model, &b_t));    /* 2 */
    CHECK(ANeuralNetworksModel_addOperand(model, &act_t));  /* 3 */
    CHECK(ANeuralNetworksModel_addOperand(model, &out_t));  /* 4 */

    static int32_t *bias;
    if (!bias) { bias = calloc(N, sizeof(int32_t)); }
    int32_t none = ANEURALNETWORKS_FUSED_NONE;
    CHECK(ANeuralNetworksModel_setOperandValue(model, 1, T, (size_t)N * D));
    CHECK(ANeuralNetworksModel_setOperandValue(model, 2, bias,
                                               (size_t)N * sizeof(int32_t)));
    CHECK(ANeuralNetworksModel_setOperandValue(model, 3, &none, sizeof none));

    uint32_t ins[4] = {0, 1, 2, 3}, outs[1] = {4};
    CHECK(ANeuralNetworksModel_addOperation(model,
            ANEURALNETWORKS_FULLY_CONNECTED, 4, ins, 1, outs));
    uint32_t mi[1] = {0}, mo[1] = {4};
    CHECK(ANeuralNetworksModel_identifyInputsAndOutputs(model, 1, mi, 1, mo));
    CHECK(ANeuralNetworksModel_finish(model));
    *out = model;
    return 0;
}

/* Run on a specific device (or NULL = let the runtime choose). Returns the
 * dequantised outputs in `got`. */
static int run_on(ANeuralNetworksModel *model, ANeuralNetworksDevice *dev,
                  float out_scale, int32_t out_zp, int8_t *raw, double *secs) {
    ANeuralNetworksCompilation *comp;
    if (dev) {
        CHECK(ANeuralNetworksCompilation_createForDevices(model, &dev, 1, &comp));
    } else {
        CHECK(ANeuralNetworksCompilation_create(model, &comp));
    }
    CHECK(ANeuralNetworksCompilation_setPreference(
              comp, ANEURALNETWORKS_PREFER_SUSTAINED_SPEED));
    CHECK(ANeuralNetworksCompilation_finish(comp));

    ANeuralNetworksExecution *exec;
    CHECK(ANeuralNetworksExecution_create(comp, &exec));
    CHECK(ANeuralNetworksExecution_setInput(exec, 0, NULL, q, D));
    CHECK(ANeuralNetworksExecution_setOutput(exec, 0, NULL, raw, N));
    double t0 = now_s();
    CHECK(ANeuralNetworksExecution_compute(exec));
    *secs = now_s() - t0;
    ANeuralNetworksExecution_free(exec);
    ANeuralNetworksCompilation_free(comp);
    (void)out_scale; (void)out_zp;
    return 0;
}

static void compare(const char *tag, const int8_t *raw, float scale,
                    int32_t zp, double secs) {
    /* dequantise and compare with the exact reference */
    int exact = 0, within1 = 0, worst = 0;
    long clipped = 0;
    for (int r = 0; r < N; r++) {
        int32_t deq = (int32_t)llround(((double)raw[r] - zp) * (double)scale);
        int32_t err = deq - ref[r];
        if (err < 0) err = -err;
        if (err == 0) exact++;
        if (err <= (int32_t)llround(scale)) within1++;
        if (err > worst) worst = err;
        if (raw[r] == -128 || raw[r] == 127) clipped++;
    }
    /* the question that actually matters: after requantisation, does a
     * threshold still separate the planted matches from everything else? */
    int32_t cutoff = 0;
    for (int r = 0; r < N; r++) if (ref[r] > cutoff) cutoff = ref[r];
    int tp = 0, fp = 0;
    int32_t q_cut = (int32_t)llround((double)cutoff / (double)scale);
    for (int r = 0; r < N; r++) {
        int hit = raw[r] >= q_cut;               /* grid-snapped cutoff */
        int truth = ref[r] >= cutoff;
        if (hit && truth) tp++;
        if (hit && !truth) fp++;
    }
    int truth_n = 0; for (int r = 0; r < N; r++) if (ref[r] >= cutoff) truth_n++;
    printf("  %-22s scale %8.4f | exact %5d/%d | worst err %6d | sat %5ld"
           " | grid cutoff %4d -> recall %d/%d fp %d | %.1f ms\n",
           tag, scale, exact, N, worst, clipped, q_cut, tp, truth_n, fp,
           secs * 1e3);
}

int main(void) {
    make_data(0xC0FFEE);

    int32_t peak = 0;
    for (int r = 0; r < N; r++) { int32_t a = ref[r] < 0 ? -ref[r] : ref[r];
                                  if (a > peak) peak = a; }
    printf("S31 NNAPI probe   D=%d N=%d   |ref| peak %d\n", D, N, peak);
    printf("int8 output can represent 256 levels; covering +-%d needs a scale"
           " of at least %.3f\n\n", peak, (2.0 * peak) / 255.0);

    uint32_t ndev = 0;
    if (ANeuralNetworks_getDeviceCount(&ndev) != ANEURALNETWORKS_NO_ERROR) {
        printf("ANeuralNetworks_getDeviceCount failed\n");
        return 1;
    }
    printf("NNAPI devices: %u\n", ndev);
    ANeuralNetworksDevice *devs[16];
    const char *names[16];
    int32_t types[16];
    for (uint32_t i = 0; i < ndev && i < 16; i++) {
        ANeuralNetworks_getDevice(i, &devs[i]);
        ANeuralNetworksDevice_getName(devs[i], &names[i]);
        ANeuralNetworksDevice_getType(devs[i], &types[i]);
        int64_t fl = 0; ANeuralNetworksDevice_getFeatureLevel(devs[i], &fl);
        const char *tn = types[i] == ANEURALNETWORKS_DEVICE_CPU ? "CPU"
                       : types[i] == ANEURALNETWORKS_DEVICE_GPU ? "GPU"
                       : types[i] == ANEURALNETWORKS_DEVICE_ACCELERATOR ? "ACCELERATOR"
                       : types[i] == ANEURALNETWORKS_DEVICE_OTHER ? "OTHER" : "UNKNOWN";
        printf("  [%u] %-40s %-12s feature level %" PRId64 "\n",
               i, names[i], tn, fl);
    }
    putchar('\n');

    int8_t *raw = malloc(N);
    double secs;

    /* Two declared output scales. If the runtime honours what we declare,
     * the results differ in exactly the way the scale predicts — which is
     * what "the scale is pinned by the job" means. */
    float scales[2] = {(float)((2.0 * peak) / 255.0), 16.0f};
    for (int s = 0; s < 2; s++) {
        ANeuralNetworksModel *model;
        if (build_model(&model, scales[s], 0) != 0) return 1;

        printf("declared output scale %.4f\n", scales[s]);
        if (run_on(model, NULL, scales[s], 0, raw, &secs) == 0)
            compare("runtime's choice", raw, scales[s], 0, secs);
        for (uint32_t i = 0; i < ndev && i < 16; i++) {
            if (run_on(model, devs[i], scales[s], 0, raw, &secs) == 0)
                compare(names[i], raw, scales[s], 0, secs);
            else
                printf("  %-22s cannot run this model\n", names[i]);
        }
        ANeuralNetworksModel_free(model);
        putchar('\n');
    }
    return 0;
}
