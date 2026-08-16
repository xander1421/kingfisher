/* What is this phone's achievable READ bandwidth? The prefilter streams 12.8 MB
 * per query and nothing else, so its ceiling is a pure read roof, not copy. */
#include <arm_neon.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#define MB 128
static uint64_t *buf; static size_t N;
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
typedef struct{size_t lo,hi;uint64_t acc;}rg_t;
static void*rd(void*a){rg_t*r=a;uint64x2_t s=vdupq_n_u64(0);
  for(size_t i=r->lo;i<r->hi;i+=2)s=vaddq_u64(s,vld1q_u64(buf+i));
  r->acc=vgetq_lane_u64(s,0)+vgetq_lane_u64(s,1);return 0;}
int main(int argc,char**argv){int nt=argc>1?atoi(argv[1]):4;
  N=(size_t)MB*1024*1024/8; buf=malloc(N*8);
  for(size_t i=0;i<N;i++)buf[i]=i;
  pthread_t th[64];rg_t rg[64];double best=1e18;
  for(int r=0;r<7;r++){double t0=now();
    size_t c=(N+nt-1)/nt;
    for(int t=0;t<nt;t++){rg[t].lo=t*c;rg[t].hi=(t+1)*c>N?N:(t+1)*c;pthread_create(&th[t],0,rd,&rg[t]);}
    uint64_t s=0;for(int t=0;t<nt;t++){pthread_join(th[t],0);s+=rg[t].acc;}
    double e=now()-t0;if(r&&e<best)best=e;if(s==42)printf("");}
  printf("%d threads  %.1f GB/s  (%d MB read in %.2f ms)\n",nt,(double)MB*1048576/best/1e9,MB,best*1e3);
  return 0;}
