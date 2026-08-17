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
        // Characterising the aliasing class: is divergence statically
        // predictable from the program text? If yes, admission control can ban
        // it and WorkManager's process reuse stays viable. If no, the device
        // agent needs a process per job.
        Map<String, String> progs = new LinkedHashMap<>();

        // --- A. two pattern vars onto one data var (the known-divergent shape)
        progs.put("A1_alias2",   "(pair $z $z)\n!(match &self (pair $x $y) ($x $y))\n");
        progs.put("A2_alias3",   "(tri $z $z $z)\n!(match &self (tri $x $y $w) ($x $y $w))\n");
        progs.put("A3_proj1",    "(pair $z $z)\n!(match &self (pair $x $y) $x)\n");
        progs.put("A4_nested",   "(o (i $z $z))\n!(match &self (o (i $x $y)) ($x $y))\n");

        // --- B. no aliasing: distinct data vars, or ground terms
        progs.put("B1_distinct", "(pair $z $w)\n!(match &self (pair $x $y) ($x $y))\n");
        progs.put("B2_ground",   "(pair A A)\n!(match &self (pair $x $y) ($x $y))\n");
        progs.put("B3_samevar",  "(pair $z $z)\n!(match &self (pair $x $x) $x)\n");
        progs.put("B4_novar",    "(pair A B)\n!(match &self (pair $x $y) ($x $y))\n");

        // --- C. aliasing created by a RULE rather than by stored data
        progs.put("C1_rulealias","(= (f $x) (g $x $x))\n!(f Q)\n");
        progs.put("C2_rulevar",  "(= (f $x) (g $x $x))\n(h $v)\n!(match &self (h $k) (f $k))\n");

        // --- D. separating "data contains ANY variable" from "data REPEATS a variable"
        progs.put("D1_onevar",   "(pair $z A)\n!(match &self (pair $x $y) ($x $y))\n");
        progs.put("D2_twovars",  "(pair $z $w)\n!(match &self (pair $x $y) ($x $y))\n");
        progs.put("D3_repeat3",  "(tri $z $z A)\n!(match &self (tri $x $y $w) ($x $y $w))\n");
        progs.put("D4_crossatom","(one $z)\n(two $z)\n!(match &self (one $x) (match &self (two $y) ($x $y)))\n");

        // --- controls
        progs.put("CTL_arith",   "!(+ 1 2)\n");
        progs.put("POSCTL_space","!(new-space)\n");

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
