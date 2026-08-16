/* Disable bionic heap pointer tagging for the whole process.
 *
 * Android 11+ tags heap pointers in the top byte (TBI). PathMap's `slim_ptrs`
 * feature packs its own bits into 64-bit inter-node pointers, so bionic sees a
 * tag it did not issue and aborts:
 *   "Pointer tag for 0x... was truncated"
 * An app would set android:allowNativeHeapPointerTagging="false" in its
 * manifest; a bare executable has no manifest, so we LD_PRELOAD this instead.
 *
 * M_BIONIC_SET_HEAP_TAGGING_LEVEL = -204, M_HEAP_TAGGING_LEVEL_NONE = 0
 * (bionic/libc/include/malloc.h)
 */
#include <malloc.h>
#include <stdio.h>
#include <stdlib.h>

__attribute__((constructor))
static void disable_heap_tagging(void) {
    int ok = mallopt(-204 /* M_BIONIC_SET_HEAP_TAGGING_LEVEL */, 0 /* NONE */);
    if (getenv("NOTAG_VERBOSE")) fprintf(stderr, "[notag] mallopt -> %d\n", ok);
}
