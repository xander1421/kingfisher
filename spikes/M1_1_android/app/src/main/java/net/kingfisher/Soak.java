package net.kingfisher;

import android.util.Log;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/**
 * Does job N differ from job 1 inside ONE process?
 *
 * PORT_PLAN M1.3 requires a fresh process per job, with two derivations:
 *   (1) S60/A8 -- a reused `Metta` pollutes the atomspace. A fresh metta_t per
 *       job addresses this, and this harness does that.
 *   (2) NEXT_VARIABLE_ID is process-global, so job N occupies a different
 *       variable-id space than job 1. A fresh metta_t does NOT reset it.
 *
 * WorkManager reuses the app process, so (2) is the derivation that decides
 * whether the platform model is usable. This measures it.
 */
public final class Soak {

    static final String TAG = "KFSOAK";

    static String sha(String s) throws Exception {
        byte[] d = MessageDigest.getInstance("SHA-256").digest(s.getBytes("UTF-8"));
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < 8; i++) b.append(String.format("%02x", d[i]));
        return b.toString();
    }

    public static void run(String wd) {
        // Issue 3's probe: two distinct variables matched against one, which is
        // where make_variables_unique draws fresh ids. Plus a rule-instantiation
        // program, an arithmetic control, and a KNOWN-nondeterministic program
        // so the harness is shown able to detect difference at all.
        Map<String, String> progs = new LinkedHashMap<>();
        // the earlier form matched an atom that was never added and returned
        // EMPTY -- a vacuous probe that reads as STABLE. Add it first.
        progs.put("var_alias",  "(pair $z $z)\n!(match &self (pair $x $y) ($x $y))\n");
        progs.put("rule_inst",  "(= (f $x) (g $x $x))\n(= (g $a $b) (h $b $a))\n!(f Q)\n");
        progs.put("chain",      "(= (p $x) (q $x))\n(= (q $x) (r $x))\n!(p Z)\n!(p W)\n");
        progs.put("arith_ctl",  "!(+ 1 2)\n");
        // Control history, kept because each failure was silent:
        //   (flip)                 -- Python-ext atom, absent from Rust stdlib, echoed
        //   (random-int &rng ...)  -- &rng unbound, echoed
        // (new-space) prints a heap address (hyperon Issue 2, unpatched at 3f76dc4)
        // so it MUST vary between calls in one process. If this reads STABLE the
        // harness cannot see in-process variation and every row above is void.
        progs.put("POSCTL_space", "!(new-space)\n");

        int reps = 40;
        for (Map.Entry<String, String> e : progs.entrySet()) {
            Set<String> seen = new LinkedHashSet<>();
            String first = null, lastOut = "";
            int firstDiffAt = -1;
            for (int i = 0; i < reps; i++) {
                String out;
                try {
                    out = Metta.run(e.getValue(), wd);   // FRESH metta_t each time
                } catch (Throwable t) { out = "THREW " + t; }
                lastOut = out.trim().replace("\n", " | ");
                String h;
                try { h = sha(out); } catch (Exception ex) { h = "hashfail"; }
                if (first == null) first = h;
                else if (!h.equals(first) && firstDiffAt < 0) firstDiffAt = i;
                seen.add(h);
            }
            Log.i(TAG, "  sample[" + e.getKey() + "] = " + lastOut);
            Log.i(TAG, String.format("%-12s reps=%d distinct=%d firstDiffAt=%s %s",
                    e.getKey(), reps, seen.size(),
                    firstDiffAt < 0 ? "-" : String.valueOf(firstDiffAt),
                    seen.size() == 1 ? "STABLE" : "DIVERGES " + seen));
        }
        Log.i(TAG, "SOAK DONE");
    }
}
