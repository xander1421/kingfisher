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

    static final java.util.regex.Pattern VARID =
            java.util.regex.Pattern.compile("\\$([^\\s()#]+)#(\\d+)");

    /** Renumber variables by first appearance. See harness/canon.py for why
     *  renumbering rather than stripping: ($x#1 $x#2) and ($x#1 $x#1) are
     *  different answers and must not collapse onto each other. */
    static String canon(String t) {
        java.util.Map<String,Integer> map = new LinkedHashMap<>();
        java.util.regex.Matcher m = VARID.matcher(t);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            String key = m.group(1) + "#" + m.group(2);
            Integer k = map.get(key);
            if (k == null) { k = map.size() + 1; map.put(key, k); }
            m.appendReplacement(sb, java.util.regex.Matcher.quoteReplacement(
                    "$" + m.group(1) + "#" + k));
        }
        m.appendTail(sb);
        return sb.toString();
    }

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

        // --- E. is the hazard a property of the DATA, or of the (data,query) PAIR?
        // Data-only banning rejects 51% of hyperon's own corpus, so this decides
        // whether that rule is even on the right axis.
        String impl = "(implies (Frog $x) (Green $x))\n";
        progs.put("E1_noalias",  impl + "!(match &self (implies $p $q) ($p $q))\n");
        progs.put("E2_alias",    impl + "!(match &self (implies (Frog $a) (Green $b)) ($a $b))\n");
        String rule = "(= (f $x) (g $x $x))\n";
        progs.put("E3_rulequery",rule + "!(match &self (= $h $b) ($h $b))\n");
        // E4_typedecl removed: `(match &self (: $n $t) ...)` matches EVERY type
        // declaration in the loaded stdlib, returning thousands of atoms and
        // OOM-killing the process before the controls run. A probe whose scope
        // is the whole stdlib measures the stdlib, not the hypothesis.

        // --- controls
        progs.put("CTL_arith",   "!(+ 1 2)\n");
        progs.put("POSCTL_space","!(new-space)\n");

        // controls first, so a crash later cannot cost us the control (E4 did
        // exactly that: the process died before POSCTL ever ran)
        Map<String, String> ordered = new LinkedHashMap<>();
        for (String k : new String[]{"CTL_arith", "POSCTL_space"})
            if (progs.containsKey(k)) ordered.put(k, progs.remove(k));
        ordered.putAll(progs);
        progs = ordered;

        int reps = 40;
        for (Map.Entry<String, String> e : progs.entrySet()) {
            Set<String> seen = new LinkedHashSet<>();
            Set<String> seenCanon = new LinkedHashSet<>();
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
                try { seenCanon.add(sha(canon(out))); } catch (Exception ex) {}
            }
            Log.i(TAG, "  sample[" + e.getKey() + "] = " + lastOut);
            Log.i(TAG, String.format("%-13s raw=%2d canon=%2d  %s",
                    e.getKey(), seen.size(), seenCanon.size(),
                    seenCanon.size() == 1
                        ? (seen.size() == 1 ? "stable both" : "FIXED BY CANON")
                        : "STILL DIVERGES"));
        }
        Log.i(TAG, "SOAK DONE");
    }
}
