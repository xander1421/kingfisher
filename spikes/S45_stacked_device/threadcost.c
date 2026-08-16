/* How much of the "scaling" is just pthread_create/join? */
#include <pthread.h>
#include <stdio.h>
#include <time.h>
static void *noop(void *a){ (void)a; return 0; }
static double now(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
                         return t.tv_sec + t.tv_nsec*1e-9; }
int main(void){
    pthread_t th[64];
    printf("%8s %14s %14s\n","threads","spawn+join_us","per_thread_us");
    for (int n = 1; n <= 8; n *= 2) {
        double best = 1e18;
        for (int r = 0; r < 20; r++) {
            double t0 = now();
            for (int i = 0; i < n; i++) pthread_create(&th[i], NULL, noop, NULL);
            for (int i = 0; i < n; i++) pthread_join(th[i], NULL);
            double e = now() - t0;
            if (e < best) best = e;
        }
        printf("%8d %14.1f %14.1f\n", n, best*1e6, best*1e6/n);
    }
    return 0;
}
