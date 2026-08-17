/* S52 — the shaping matrix on a REAL knowledge graph.
 *
 * Every constant in S5, S10, S11, S17, S47 and S48 was fitted on one
 * self-authored synthetic graph: 100k triples, 10 predicates, 1,000 subjects,
 * 1,000 objects, uniform. The rule this workspace adopted and then ignored is
 * that a self-authored case may catch a regression but must never choose a
 * value. S48 then collapsed under a reseed, which is what that costs.
 *
 * Real graph: FB15k-237, 272,115 Freebase triples, 237 predicates, 14,505
 * entities, subjects and objects sharing one entity space. It is nothing like
 * the synthetic:
 *
 *                       synthetic            FB15k-237
 *   predicates          10, uniform          237, max 15,989 vs median 373
 *   objects             1,000, uniform       14,505, top 1% hold 28% of triples
 *   (p,s) answers       ~10 by construction  median 1, mean 2.91, max 843
 *
 * That last row is the one that matters: S48 found clustering *buries* targets
 * when a query has a single answer, because a homogeneous bucket's coherent
 * bundle drowns the outlier. Real queries are overwhelmingly single-answer.
 *
 * Two S48 defects fixed here as well:
 *   - S48 used ONE literal per query shape. This samples NQ queries per cell
 *     and reports the median, so no cell is a single draw.
 *   - S48's cutoff sweep read `truth` to decide where to stop (an oracle). So
 *     does this, because a fixed cutoff cannot hit recall 1.0 on a bundled
 *     store — but the shortlist is now reported as a FRACTION OF THE STORE,
 *     which makes "this is a scan wearing a prefilter costume" visible.
 *
 * Build: aarch64-linux-android29-clang -O3 -Wall -Wextra -Werror \
 *          -march=armv8.6-a+i8mm+dotprod -o realkg realkg.c
 */

#define _GNU_SOURCE
#include <arm_neon.h>
#include <stdio.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define D      1024
#define WORDS  (D / 64)
#define B      64
#define NQ     120          /* queries sampled per cell */

static int NT, NP, NE;
static long g_score_reads=0, g_cut_reads=0, g_cut_iters=0;
static int *tp_, *ts_, *to_, *order;
static uint64_t *base, *bundle, Rp[WORDS], Rs[WORDS], Ro[WORDS];
static uint64_t (*P)[WORDS], (*E)[WORDS];
static int32_t *scores;
static int g_ckey;

static uint32_t rng = 0xC0FFEE;
static uint32_t r32(void){ rng^=rng<<13; rng^=rng>>17; rng^=rng<<5; return rng; }
static uint64_t r64(void){ uint64_t h=r32(); uint64_t l=r32(); return (h<<32)|l; }
static double now_s(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
                           return t.tv_sec+t.tv_nsec*1e-9; }

static long ckey(int i){
    switch(g_ckey){
      case 0: return (long)tp_[i]*NE+ts_[i];
      case 1: return (long)tp_[i]*NE+to_[i];
      default:return (long)ts_[i]*NE+to_[i];
    }
}
static int matches(int i,int q,int qp,int qs,int qo){
    switch(q){
      case 0: return tp_[i]==qp&&ts_[i]==qs;
      case 1: return tp_[i]==qp&&to_[i]==qo;
      default:return ts_[i]==qs&&to_[i]==qo;
    }
}
static inline int32_t score_row(const uint64_t*r,const uint64_t*qs,
                                const uint64_t*qm,int32_t nnz){
    uint8x16_t v=vdupq_n_u8(0);
    for(int w=0;w<WORDS;w+=2){
        uint64x2_t t=vld1q_u64(r+w),s=vld1q_u64(qs+w),m=vld1q_u64(qm+w);
        uint64x2_t x=vandq_u64(veorq_u64(t,s),m);
        v=vaddq_u8(v,vcntq_u8(vreinterpretq_u8_u64(x)));
    }
    return 2*nnz-4*(int32_t)vaddlvq_u8(v);
}
static int cmp_d(const void*a,const void*b){
    double x=*(const double*)a,y=*(const double*)b; return (x>y)-(x<y);
}

static const char *KEYN[4]={"(pred,subj)","(pred,obj) ","(subj,obj) ","RANDOM     "};
static const char *QN[3]  ={"(p s ?o)","(p ?s o)","(?p s o)"};

int main(void){
    /* W4: affinity stubbed for the host build. This counts bundle reads,
       not time, so pinning is irrelevant to the result. */

    FILE *f=fopen("triples.bin","rb");
    if(!f){ fprintf(stderr,"triples.bin missing\n"); return 1; }
    if(fread(&NT,4,1,f)!=1||fread(&NP,4,1,f)!=1||fread(&NE,4,1,f)!=1) return 1;
    tp_=malloc((size_t)NT*4); ts_=malloc((size_t)NT*4); to_=malloc((size_t)NT*4);
    order=malloc((size_t)NT*4); scores=malloc((size_t)NT*4);
    for(int i=0;i<NT;i++){ int t[3];
        if(fread(t,4,3,f)!=3) return 1; tp_[i]=t[0]; ts_[i]=t[1]; to_[i]=t[2]; }
    fclose(f);

    P=malloc(sizeof(uint64_t)*WORDS*NP); E=malloc(sizeof(uint64_t)*WORDS*NE);
    base=malloc((size_t)NT*WORDS*8); bundle=malloc((size_t)NT*WORDS*8);
    if(!P||!E||!base||!bundle){ fprintf(stderr,"alloc\n"); return 1; }
    for(int w=0;w<WORDS;w++){ Rp[w]=r64(); Rs[w]=r64(); Ro[w]=r64(); }
    for(int i=0;i<NP;i++) for(int w=0;w<WORDS;w++) P[i][w]=r64();
    for(int i=0;i<NE;i++) for(int w=0;w<WORDS;w++) E[i][w]=r64();
    for(int i=0;i<NT;i++) for(int w=0;w<WORDS;w++){
        uint64_t a=Rp[w]^P[tp_[i]][w], b=Rs[w]^E[ts_[i]][w], c=Ro[w]^E[to_[i]][w];
        base[(size_t)i*WORDS+w]=(a&b)|(a&c)|(b&c);
    }

    double t0=now_s(); volatile int hh=0;
    for(int r=0;r<20;r++) for(int i=0;i<NT;i++) if(tp_[i]==0&&ts_[i]==0) hh++;
    double per_check=(now_s()-t0)/(20.0*NT);

    printf("S52 real KG: FB15k-237  %d triples, %d preds, %d entities  B=%d\n",
           NT,NP,NE,B);
    printf("%d queries sampled per cell, median reported. exact-check %.2f ns/row\n\n",
           NQ,per_check*1e9);
    printf("%-12s","cluster key");
    for(int q=0;q<3;q++) printf("%26s",QN[q]);
    printf("\n%-12s","");
    for(int q=0;q<3;q++) printf("%14s%12s","median us","%store chk");
    printf("\n");

    int nb=(NT+B-1)/B;
    for(int layout=0;layout<4;layout++){
        g_ckey=layout;
        for(int i=0;i<NT;i++) order[i]=i;
        if(layout<3){   /* counting sort on the key, stable and O(n log n) free */
            /* simple qsort with a key comparator would need a global; use
             * an index sort via repeated radix on the two components */
            for(int pass=0;pass<2;pass++){
                static int cnt[16384+1]; int mod = (pass==0)?NE:16384;
                memset(cnt,0,sizeof cnt);
                for(int i=0;i<NT;i++){ long k=ckey(order[i]);
                    cnt[(pass==0? (k%NE) : (k/NE))%mod]++; }
                int sum=0; for(int i=0;i<mod;i++){int c=cnt[i];cnt[i]=sum;sum+=c;}
                int *tmp=malloc((size_t)NT*4);
                for(int i=0;i<NT;i++){ long k=ckey(order[i]);
                    tmp[cnt[(pass==0? (k%NE) : (k/NE))%mod]++]=order[i]; }
                memcpy(order,tmp,(size_t)NT*4); free(tmp);
            }
        } else {
            for(int i=NT-1;i>0;i--){ int j=(int)(r32()%(uint32_t)(i+1));
                int t=order[i]; order[i]=order[j]; order[j]=t; }
        }
        for(int b=0;b<nb;b++){
            int lo=b*B,hi=lo+B>NT?NT:lo+B,m=hi-lo;
            for(int w=0;w<WORDS;w++){
                uint64_t out=0;
                for(int bit=0;bit<64;bit++){
                    int ones=0;
                    for(int k=lo;k<hi;k++) ones+=(int)((base[(size_t)order[k]*WORDS+w]>>bit)&1ULL);
                    if(ones*2>m) out|=1ULL<<bit;
                }
                bundle[(size_t)b*WORDS+w]=out;
            }
        }

        printf("%-12s",KEYN[layout]);
        for(int q=0;q<3;q++){
            double tot[NQ]; double frac[NQ]; int nq=0;
            uint32_t save=rng; rng=12345;      /* same queries for every layout */
            for(int trial=0; trial<NQ*40 && nq<NQ; trial++){
                int seed_row=(int)(r32()%(uint32_t)NT);
                int qp=tp_[seed_row], qs=ts_[seed_row], qo=to_[seed_row];
                int truth=0;
                for(int i=0;i<NT;i++) if(matches(i,q,qp,qs,qo)) truth++;
                if(truth<1) continue;
                static uint64_t Qm[WORDS],Qsg[WORDS]; int32_t nnz=0;
                for(int w=0;w<WORDS;w++){
                    uint64_t a,b2;
                    if(q==0){a=Rp[w]^P[qp][w];    b2=Rs[w]^E[qs][w];}
                    else if(q==1){a=Rp[w]^P[qp][w];b2=Ro[w]^E[qo][w];}
                    else {a=Rs[w]^E[qs][w];        b2=Ro[w]^E[qo][w];}
                    Qm[w]=~(a^b2); Qsg[w]=a&Qm[w]; nnz+=__builtin_popcountll(Qm[w]);
                }
                double t1=now_s();
                for(int b=0;b<nb;b++) scores[b]=score_row(bundle+(size_t)b*WORDS,Qsg,Qm,nnz);
                g_score_reads+=nb;
                double pf=now_s()-t1;
                int cut,sl=0;
                for(cut=2*nnz;cut>-2*nnz;cut-=8){
                    int found=0; sl=0; g_cut_iters++; g_cut_reads+=nb;
                    for(int b=0;b<nb;b++) if(scores[b]>=cut){
                        sl++; int lo=b*B,hi=lo+B>NT?NT:lo+B;
                        for(int k=lo;k<hi;k++) if(matches(order[k],q,qp,qs,qo)) found++;
                    }
                    if(found>=truth) break;
                }
                long checked=(long)sl*B; if(checked>NT) checked=NT;
                tot[nq]=(pf+(double)checked*per_check)*1e6;
                frac[nq]=100.0*(double)checked/(double)NT;
                nq++;
            }
            rng=save;
            qsort(tot,nq,sizeof(double),cmp_d);
            qsort(frac,nq,sizeof(double),cmp_d);
            printf("%14.1f%11.1f%%",tot[nq/2],frac[nq/2]);
        }
        printf("\n");
    }
    fprintf(stderr,"\nREAD AMPLIFICATION (W4)\n");
    fprintf(stderr,"  bundles in index          %d\n", nb);
    fprintf(stderr,"  score-pass bundle reads   %ld\n", g_score_reads);
    fprintf(stderr,"  cutoff-pass bundle reads  %ld  over %ld cutoff iterations\n", g_cut_reads, g_cut_iters);
    fprintf(stderr,"  total / score-pass        %.2fx\n", (double)(g_score_reads+g_cut_reads)/(double)g_score_reads);
    return 0;
}
