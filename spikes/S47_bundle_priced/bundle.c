/* S47 — the bundling trade, both sides, on the device, with the real encoding.
 *
 * S46 measured that a smaller store is faster in exact proportion to its size
 * (32x at B=64) but used random bits and never checked whether the answers
 * survive. S11 measured recall on the laptop and S17 then showed the recall
 * argument was recoverable by loosening the cutoff on any layout. S44 priced
 * both sides but on the host, in numpy.
 *
 * So the decision input for M2/M4 is still missing: on real silicon, with the
 * real encoding, what does bundling cost in stage-2 work once you have bought
 * its speed, and does the total go up or down?
 *
 * For each B and layout:
 *   build the bundled store   (majority over B member vectors)
 *   sweep the cutoff to find the loosest threshold giving recall 1.0
 *   measure prefilter time at that B
 *   count the rows the CPU must then exact-check
 *   total = prefilter + shortlist * measured_cost_per_exact_check
 *
 * Clustered = triples sorted by (pred,subj) before bundling, so a bucket tends
 * to share the query's bound slots. Random = shuffled. That contrast is S11's
 * central claim and it has never run on a phone.
 */

#include <arm_neon.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define D       1024
#define WORDS   (D / 64)
#define NROWS   100000
#define NPRED   10
#define NSUBJ   1000
#define NOBJ    1000
#define REPS    9

static uint64_t Rp[WORDS], Rs[WORDS], Ro[WORDS];
static uint64_t (*P)[WORDS], (*S)[WORDS], (*O)[WORDS];
static uint64_t *base;                 /* per-triple vectors, NROWS x WORDS */
static uint64_t *bundle;               /* bundled store */
static int32_t  *scores;
static int *tp_, *ts_, *to_, *order;

static double now_s(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
                           return t.tv_sec + t.tv_nsec*1e-9; }

static uint32_t rs_ = 0xC0FFEE;
static uint32_t nxt(void){ rs_^=rs_<<13; rs_^=rs_>>17; rs_^=rs_<<5; return rs_; }

/* score a packed row against the query bitplanes */
static inline int32_t score_row(const uint64_t *row, const uint64_t *qs,
                                const uint64_t *qm, int32_t nnz) {
    uint8x16_t v = vdupq_n_u8(0);
    for (int w = 0; w < WORDS; w += 2) {
        uint64x2_t t = vld1q_u64(row + w);
        uint64x2_t s = vld1q_u64(qs + w);
        uint64x2_t m = vld1q_u64(qm + w);
        uint64x2_t x = vandq_u64(veorq_u64(t, s), m);
        v = vaddq_u8(v, vcntq_u8(vreinterpretq_u8_u64(x)));
    }
    return 2 * nnz - 4 * (int32_t)vaddlvq_u8(v);
}

int main(void) {
    P = malloc(sizeof(uint64_t)*WORDS*NPRED);
    S = malloc(sizeof(uint64_t)*WORDS*NSUBJ);
    O = malloc(sizeof(uint64_t)*WORDS*NOBJ);
    base   = malloc((size_t)NROWS*WORDS*8);
    bundle = malloc((size_t)NROWS*WORDS*8);
    scores = malloc((size_t)NROWS*4);
    tp_ = malloc(NROWS*4); ts_ = malloc(NROWS*4); to_ = malloc(NROWS*4);
    order = malloc(NROWS*4);

    for (int w=0;w<WORDS;w++){ Rp[w]=((uint64_t)nxt()<<32)|nxt();
                               Rs[w]=((uint64_t)nxt()<<32)|nxt();
                               Ro[w]=((uint64_t)nxt()<<32)|nxt(); }
    for (int i=0;i<NPRED;i++) for(int w=0;w<WORDS;w++) P[i][w]=((uint64_t)nxt()<<32)|nxt();
    for (int i=0;i<NSUBJ;i++) for(int w=0;w<WORDS;w++) S[i][w]=((uint64_t)nxt()<<32)|nxt();
    for (int i=0;i<NOBJ ;i++) for(int w=0;w<WORDS;w++) O[i][w]=((uint64_t)nxt()<<32)|nxt();

    for (int i=0;i<NROWS;i++){
        tp_[i]=nxt()%NPRED; ts_[i]=nxt()%NSUBJ; to_[i]=nxt()%NOBJ;
        for (int w=0;w<WORDS;w++){
            uint64_t a=Rp[w]^P[tp_[i]][w], b=Rs[w]^S[ts_[i]][w], c=Ro[w]^O[to_[i]][w];
            base[(size_t)i*WORDS+w] = (a&b)|(a&c)|(b&c);
        }
    }

    /* Two query shapes. The store is always clustered by (pred,subj).
     *   QSHAPE 0: (p s ?o) -- the query key IS the cluster key. This is S11's
     *             configuration and AGENT-1's own C3 objection: clustering by
     *             the thing you then query by is close to circular.
     *   QSHAPE 1: (p ?s o) -- bound on pred and OBJ, which the clustering does
     *             nothing for. Answers are scattered across every bucket.
     * If clustered bundling only wins on shape 0, M4's justification is
     * conditional on knowing the query distribution in advance. */
    int qshape = getenv("QSHAPE") ? atoi(getenv("QSHAPE")) : 0;
    int qp=tp_[42], qs_i=ts_[42], qo_i=to_[42];
    static uint64_t Qm[WORDS], Qsg[WORDS]; int32_t nnz=0;
    for (int w=0;w<WORDS;w++){
        uint64_t a=Rp[w]^P[qp][w];
        uint64_t b= qshape==0 ? (Rs[w]^S[qs_i][w]) : (Ro[w]^O[qo_i][w]);
        Qm[w]=~(a^b); Qsg[w]=a&Qm[w]; nnz+=__builtin_popcountll(Qm[w]);
    }
    int truth=0;
    for(int i=0;i<NROWS;i++)
        if (qshape==0 ? (tp_[i]==qp&&ts_[i]==qs_i) : (tp_[i]==qp&&to_[i]==qo_i)) truth++;

    /* cost of ONE exact check, measured not assumed */
    double t0=now_s(); volatile int hit=0;
    for (int r=0;r<50;r++) for(int i=0;i<NROWS;i++)
        if (qshape==0 ? (tp_[i]==qp&&ts_[i]==qs_i) : (tp_[i]==qp&&to_[i]==qo_i)) hit++;
    double per_check = (now_s()-t0)/(50.0*NROWS);

    printf("S47 bundling priced   n=%d D=%d  QSHAPE=%d (%s)  truth=%d  exact-check %.2f ns/row\n",
           NROWS, D, qshape,
           qshape==0? "(p s ?o) == cluster key" : "(p ?s o) != cluster key",
           truth, per_check*1e9);
    printf("%5s %-10s %9s %10s %11s %10s %11s %11s\n",
           "B","layout","buckets","store_KB","prefilt_us","shortlist","stage2_us","total_us");

    int Bs[]={1,4,16,64};
    for (int bi=0; bi<4; bi++) {
      for (int layout=0; layout<2; layout++) {   /* 0 clustered, 1 random */
        int B=Bs[bi];
        for (int i=0;i<NROWS;i++) order[i]=i;
        if (layout==0) {                          /* cluster by (pred,subj) */
            for (int i=1;i<NROWS;i++){            /* insertion on key, stable */
                int k=order[i], j=i-1;
                long kk=(long)tp_[k]*NSUBJ+ts_[k];
                while(j>=0 && (long)tp_[order[j]]*NSUBJ+ts_[order[j]] > kk){
                    order[j+1]=order[j]; j--; }
                order[j+1]=k;
            }
        } else {
            for (int i=NROWS-1;i>0;i--){ int j=nxt()%(i+1);
                int t=order[i]; order[i]=order[j]; order[j]=t; }
        }

        int nb=(NROWS+B-1)/B;
        for (int b=0;b<nb;b++){
            int lo=b*B, hi=lo+B>NROWS?NROWS:lo+B, m=hi-lo;
            for (int w=0;w<WORDS;w++){
                if (m==1){ bundle[(size_t)b*WORDS+w]=base[(size_t)order[lo]*WORDS+w]; continue; }
                /* majority across the bucket's members, bit by bit */
                uint64_t out=0;
                for (int bit=0;bit<64;bit++){
                    int ones=0;
                    for (int k=lo;k<hi;k++)
                        ones += (base[(size_t)order[k]*WORDS+w]>>bit)&1ULL;
                    if (ones*2 > m) out |= 1ULL<<bit;
                }
                bundle[(size_t)b*WORDS+w]=out;
            }
        }

        /* loosest cutoff giving recall 1.0 */
        for (int b=0;b<nb;b++) scores[b]=score_row(bundle+(size_t)b*WORDS,Qsg,Qm,nnz);
        int cut, shortlist=0;
        for (cut=2*nnz; cut> -2*nnz; cut-=8) {
            int found=0; shortlist=0;
            for (int b=0;b<nb;b++) if (scores[b]>=cut){
                shortlist++;
                int lo=b*B, hi=lo+B>NROWS?NROWS:lo+B;
                for(int k=lo;k<hi;k++)
                    if (qshape==0 ? (tp_[order[k]]==qp&&ts_[order[k]]==qs_i)
                                  : (tp_[order[k]]==qp&&to_[order[k]]==qo_i)) found++;
            }
            if (found>=truth) break;
        }
        int checked = shortlist*B; if (checked>NROWS) checked=NROWS;

        double best=1e18;
        for (int r=0;r<REPS;r++){
            double s0=now_s();
            for (int b=0;b<nb;b++) scores[b]=score_row(bundle+(size_t)b*WORDS,Qsg,Qm,nnz);
            double e=now_s()-s0; if(r&&e<best)best=e;
        }
        double stage2 = checked*per_check;
        printf("%5d %-10s %9d %10.1f %11.1f %10d %11.1f %11.1f\n",
               B, layout? "random":"clustered", nb, (double)nb*WORDS*8/1024.0,
               best*1e6, checked, stage2*1e6, (best+stage2)*1e6);
      }
    }
    return 0;
}
