/* S52 — attack on S50's null control.
 *
 * bench.h rule 3: "NULL. Time an empty bracket the same way ... If null > 1% of
 * the measurement, bench_report prints DISQUALIFIED."
 *
 * But the two brackets do not have the same shape:
 *     measurement:  for (i<inner) fn(ctx);          <- INDIRECT call, cannot inline
 *     null:         for (i<inner) bench_noop(ctx);  <- static inline, direct
 *
 * If the null bracket optimises away, null_ns ~ 0 and the DISQUALIFIED gate can
 * never fire, whatever the real per-call overhead is. This measures both shapes.
 */
#include <stdio.h>
#include <stdint.h>
#include <time.h>

static uint64_t now_ns(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
    return (uint64_t)t.tv_sec*1000000000ull+(uint64_t)t.tv_nsec; }

typedef uint64_t (*bench_fn)(void*);

/* exactly S50's null */
static inline uint64_t bench_noop(void *ctx){ (void)ctx; return 0; }
/* the same function reached the way a real kernel is reached */
static uint64_t noop_indirect(void *ctx){ (void)ctx; return 0; }

static volatile bench_fn sink;

int main(void){
    const long inner = 20000000L;
    volatile uint64_t d = 0;

    uint64_t t0 = now_ns();
    for (long i=0;i<inner;i++) d = bench_noop(0);
    double a = (double)(now_ns()-t0)/inner;

    bench_fn fn = noop_indirect; sink = fn;
    t0 = now_ns();
    for (long i=0;i<inner;i++) d = fn(0);
    double b = (double)(now_ns()-t0)/inner;
    (void)d;

    printf("S50 null bracket   (static inline, as written) : %8.3f ns/iter\n", a);
    printf("same call INDIRECT (as the measurement is)     : %8.3f ns/iter\n", b);
    printf("understated by                                  : %8.1fx\n", b/(a>0?a:1e-9));
    printf("\nS50 smallest store = 195 rows ~ 1100 ns/iter\n");
    printf("  gate uses null = %.3f ns  -> %.4f%% of result  -> never fires\n", a, 100*a/1100.0);
    printf("  true call shape = %.3f ns  -> %.4f%% of result\n", b, 100*b/1100.0);
    return 0;
}
