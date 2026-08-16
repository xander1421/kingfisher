/* S48 — "a shard shaped for yesterday's queries": the shaping/query mismatch
 * matrix, measured on device.
 *
 * S47 answered AGENT-1's C3 with one mismatched shape, and I flagged its limit
 * myself: the real question is not one mismatch, it is what happens when the
 * query distribution MOVES after the shard is laid out. Shaping is sold as "a
 * job whose product makes all future jobs cheaper". If that benefit decays as
 * queries drift, "all future jobs" has a half-life, and nobody has measured it.
 *
 * Cluster the store by each of the three key pairs; query each of the three
 * two-bound shapes; B=64; recall forced to 1.0 everywhere by sweeping the
 * cutoff. Diagonal = the shaper guessed right. Off-diagonal = drift. The random
 * layout is the no-shaping floor.
 *
 * Build: aarch64-linux-android29-clang -O3 -march=armv8.6-a+i8mm+dotprod \
 *          -o decay decay.c
 */

#include <arm_neon.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define D      1024
#define WORDS  (D/64)
#define NROWS  100000
#define NPRED  10
#define NSUBJ  1000
#define NOBJ   1000
#define B      64
#define REPS   7

static uint64_t Rp[WORDS],Rs[WORDS],Ro[WORDS];
static uint64_t (*P)[WORDS],(*S)[WORDS],(*O)[WORDS];
static uint64_t *base,*bundle;
static int32_t  *scores;
static int *tp_,*ts_,*to_,*order;
static int g_ckey;

static double now_s(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
                          return t.tv_sec+t.tv_nsec*1e-9;}
static uint32_t rs_=0xC0FFEE;
static uint32_t nxt(void){rs_^=rs_<<13;rs_^=rs_>>17;rs_^=rs_<<5;return rs_;}

static long ckey(int i){
    switch(g_ckey){
      case 0: return (long)tp_[i]*NSUBJ+ts_[i];   /* (pred,subj) */
      case 1: return (long)tp_[i]*NOBJ +to_[i];   /* (pred,obj)  */
      default:return (long)ts_[i]*NOBJ +to_[i];   /* (subj,obj)  */
    }
}
/* does triple i satisfy query shape q with the pinned literals? */
static int matches(int i,int q,int qp,int qs,int qo){
    switch(q){
      case 0: return tp_[i]==qp&&ts_[i]==qs;      /* (p s ?o) */
      case 1: return tp_[i]==qp&&to_[i]==qo;      /* (p ?s o) */
      default:return ts_[i]==qs&&to_[i]==qo;      /* (?p s o) */
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

static const char *KEYN[3]={"(pred,subj)","(pred,obj) ","(subj,obj) "};
static const char *QN[3]  ={"(p s ?o)","(p ?s o)","(?p s o)"};

int main(void){
    P=malloc(sizeof(uint64_t)*WORDS*NPRED); S=malloc(sizeof(uint64_t)*WORDS*NSUBJ);
    O=malloc(sizeof(uint64_t)*WORDS*NOBJ);
    base=malloc((size_t)NROWS*WORDS*8); bundle=malloc((size_t)NROWS*WORDS*8);
    scores=malloc((size_t)NROWS*4);
    tp_=malloc(NROWS*4);ts_=malloc(NROWS*4);to_=malloc(NROWS*4);order=malloc(NROWS*4);

    for(int w=0;w<WORDS;w++){Rp[w]=((uint64_t)nxt()<<32)|nxt();
                             Rs[w]=((uint64_t)nxt()<<32)|nxt();
                             Ro[w]=((uint64_t)nxt()<<32)|nxt();}
    for(int i=0;i<NPRED;i++)for(int w=0;w<WORDS;w++)P[i][w]=((uint64_t)nxt()<<32)|nxt();
    for(int i=0;i<NSUBJ;i++)for(int w=0;w<WORDS;w++)S[i][w]=((uint64_t)nxt()<<32)|nxt();
    for(int i=0;i<NOBJ ;i++)for(int w=0;w<WORDS;w++)O[i][w]=((uint64_t)nxt()<<32)|nxt();
    for(int i=0;i<NROWS;i++){
        tp_[i]=nxt()%NPRED;ts_[i]=nxt()%NSUBJ;to_[i]=nxt()%NOBJ;
        for(int w=0;w<WORDS;w++){
            uint64_t a=Rp[w]^P[tp_[i]][w],b=Rs[w]^S[ts_[i]][w],c=Ro[w]^O[to_[i]][w];
            base[(size_t)i*WORDS+w]=(a&b)|(a&c)|(b&c);
        }
    }
    int qp=tp_[42],qs_i=ts_[42],qo_i=to_[42];

    double t0=now_s();volatile int hh=0;
    for(int r=0;r<30;r++)for(int i=0;i<NROWS;i++)if(matches(i,0,qp,qs_i,qo_i))hh++;
    double per_check=(now_s()-t0)/(30.0*NROWS);

    printf("S48 shaping decay   n=%d D=%d B=%d   exact-check %.2f ns/row\n",
           NROWS,D,B,per_check*1e9);
    printf("all cells at recall 1.0 (cutoff swept). total us = prefilter + checked*%.2fns\n\n",
           per_check*1e9);
    printf("%-14s","cluster key");
    for(int q=0;q<3;q++) printf("%18s",QN[q]);
    printf("\n");

    double diag[3]={0,0,0}, offmax=0;
    for(int layout=0;layout<4;layout++){       /* 0,1,2 = key; 3 = random */
        g_ckey=layout;
        printf("%-14s", layout==3? "RANDOM (none)" : KEYN[layout]);

        for(int i=0;i<NROWS;i++)order[i]=i;
        if(layout<3){
            for(int i=1;i<NROWS;i++){int k=order[i],j=i-1;long kk=ckey(k);
                while(j>=0&&ckey(order[j])>kk){order[j+1]=order[j];j--;}
                order[j+1]=k;}
        } else {
            for(int i=NROWS-1;i>0;i--){int j=nxt()%(i+1);
                int t=order[i];order[i]=order[j];order[j]=t;}
        }
        int nb=(NROWS+B-1)/B;
        for(int b=0;b<nb;b++){
            int lo=b*B,hi=lo+B>NROWS?NROWS:lo+B,m=hi-lo;
            for(int w=0;w<WORDS;w++){
                uint64_t out=0;
                for(int bit=0;bit<64;bit++){
                    int ones=0;
                    for(int k=lo;k<hi;k++) ones+=(base[(size_t)order[k]*WORDS+w]>>bit)&1ULL;
                    if(ones*2>m) out|=1ULL<<bit;
                }
                bundle[(size_t)b*WORDS+w]=out;
            }
        }

        for(int q=0;q<3;q++){
            static uint64_t Qm[WORDS],Qsg[WORDS];int32_t nnz=0;
            for(int w=0;w<WORDS;w++){
                uint64_t a,b2;
                if(q==0){a=Rp[w]^P[qp][w];      b2=Rs[w]^S[qs_i][w];}
                else if(q==1){a=Rp[w]^P[qp][w]; b2=Ro[w]^O[qo_i][w];}
                else {a=Rs[w]^S[qs_i][w];       b2=Ro[w]^O[qo_i][w];}
                Qm[w]=~(a^b2);Qsg[w]=a&Qm[w];nnz+=__builtin_popcountll(Qm[w]);
            }
            int truth=0;for(int i=0;i<NROWS;i++)if(matches(i,q,qp,qs_i,qo_i))truth++;

            for(int b=0;b<nb;b++)scores[b]=score_row(bundle+(size_t)b*WORDS,Qsg,Qm,nnz);
            int cut,shortlist=0;
            for(cut=2*nnz;cut>-2*nnz;cut-=8){
                int found=0;shortlist=0;
                for(int b=0;b<nb;b++)if(scores[b]>=cut){
                    shortlist++;int lo=b*B,hi=lo+B>NROWS?NROWS:lo+B;
                    for(int k=lo;k<hi;k++)if(matches(order[k],q,qp,qs_i,qo_i))found++;
                }
                if(found>=truth)break;
            }
            int checked=shortlist*B;if(checked>NROWS)checked=NROWS;

            double best=1e18;
            for(int r=0;r<REPS;r++){
                double s0=now_s();
                for(int b=0;b<nb;b++)scores[b]=score_row(bundle+(size_t)b*WORDS,Qsg,Qm,nnz);
                double e=now_s()-s0;if(r&&e<best)best=e;
            }
            double total=(best+checked*per_check)*1e6;
            printf("%13.1f us",total);
            if(layout<3){
                if(layout==q) diag[q]=total;
                else if(total>offmax) offmax=total;
            }
        }
        printf("\n");
    }
    printf("\nmatched (diagonal) mean %.1f us   worst mismatch %.1f us   decay %.1fx\n",
           (diag[0]+diag[1]+diag[2])/3.0, offmax, offmax/((diag[0]+diag[1]+diag[2])/3.0));
    return 0;
}
