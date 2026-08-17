// M1.1 JNI shim: run a MeTTa program in-process inside an Android app.
// S2 proved libhyperonc links; M1.1's first half proved it loads. This runs it.
#include <jni.h>
#include <stdlib.h>
#include <string.h>
#include <android/log.h>
#include "hyperon.h"

#define TAG "KFMETTA"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, TAG, __VA_ARGS__)

typedef struct { char *buf; size_t len, cap; } sink_t;

static void sink_put(sink_t *s, const char *txt) {
    size_t n = strlen(txt);
    if (s->len + n + 2 > s->cap) {
        s->cap = (s->len + n + 2) * 2;
        s->buf = realloc(s->buf, s->cap);
    }
    memcpy(s->buf + s->len, txt, n);
    s->len += n;
    s->buf[s->len++] = '\n';
    s->buf[s->len] = 0;
}

/* metta_run hands back one atom_vec per top-level expression evaluated. */
static void on_results(const struct atom_vec_t *vec, void *ctx) {
    sink_t *s = (sink_t *)ctx;
    uintptr_t n = atom_vec_len(vec);
    for (uintptr_t i = 0; i < n; i++) {
        atom_ref_t a = atom_vec_get(vec, i);
        uintptr_t need = atom_to_str(&a, NULL, 0);      // query length first
        char *tmp = malloc(need + 1);
        atom_to_str(&a, tmp, need + 1);
        sink_put(s, tmp);
        free(tmp);
    }
}

JNIEXPORT jstring JNICALL
Java_net_kingfisher_Metta_run(JNIEnv *env, jclass cls, jstring jprog, jstring jwd) {
    const char *prog = (*env)->GetStringUTFChars(env, jprog, NULL);
    const char *wd   = (*env)->GetStringUTFChars(env, jwd, NULL);

    /* PORT_PLAN M1.1: pass an explicit working dir. The `directories` crate
     * resolves XDG paths that are not writable on Android. */
    struct env_builder_t eb = env_builder_start();
    env_builder_set_working_dir(&eb, wd);

    /* metta_new_core loads NO stdlib -- it echoes (+ 1 2) back unevaluated.
     * metta_new_with_stdlib_loader uses the default Rust stdlib and runs
     * init.metta, which is what "MeTTa runs" actually means.
     * space_ref must NOT be null: unlike its sibling metta_new_core, this
     * function dereferences it unconditionally (metta.rs:857) and a NULL
     * segfaults. The doc does not promise nullability, so this is API
     * asymmetry rather than a hyperon defect -- but it costs a crash. */
    struct space_t sp = space_new_grounding_space();
    struct metta_t m = metta_new_with_stdlib_loader(NULL, &sp, eb);
    struct sexpr_parser_t p = sexpr_parser_new(prog);

    sink_t sink = {0};
    sink.cap = 4096; sink.buf = malloc(sink.cap); sink.buf[0] = 0;
    metta_run(&m, p, on_results, &sink);

    const char *err = metta_err_str(&m);
    if (err && err[0]) {
        LOGI("metta_err_str: %s", err);
        sink_put(&sink, "ERR:");
        sink_put(&sink, err);
    }

    jstring out = (*env)->NewStringUTF(env, sink.buf ? sink.buf : "");
    free(sink.buf);
    metta_free(m);
    space_free(sp);
    (*env)->ReleaseStringUTFChars(env, jprog, prog);
    (*env)->ReleaseStringUTFChars(env, jwd, wd);
    return out;
}
