package net.kingfisher;

import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.os.PowerManager;
import android.os.StatFs;
import android.util.Log;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

/**
 * M1.3 in doWork() -- the residue WorkManager cannot express, ported from the
 * Python policy in spikes/M1_3_worker/preflight.py.
 *
 * SCHEDULER_SPEC rows 2 and 3 are both marked "Residue: yes":
 *   BatteryNotLow fires near 15%, nowhere near BOINC's 90% floor, and
 *   thermal status has no WorkManager constraint at all.
 * Measured at 98.5 us for the full gate (M1.1), i.e. 0.14% of a job, so this
 * runs PER JOB as the spec requires -- not amortised across a session, which
 * was an artifact of measuring it over adb.
 */
public class MettaWorker extends Worker {

    public static final String TAG = "KFWORKER";
    static final int THERMAL_MAX = PowerManager.THERMAL_STATUS_LIGHT;  // stop above
    static final int BATTERY_FLOOR_PCT = 90;
    static final long MIN_FREE_BYTES = 512L * 1024 * 1024;

    public MettaWorker(@NonNull Context c, @NonNull WorkerParameters p) { super(c, p); }

    /** null = go; otherwise the refusal reason. */
    private String preflight() {
        Context c = getApplicationContext();
        PowerManager pm = (PowerManager) c.getSystemService(Context.POWER_SERVICE);
        int thermal = pm.getCurrentThermalStatus();
        if (thermal > THERMAL_MAX) return "thermal:" + thermal + ">" + THERMAL_MAX;

        // SCHEDULER_SPEC:19 specifies EXTRA_LEVEL/EXTRA_SCALE -- the sticky
        // broadcast, measured 19x cheaper than getIntProperty (2.97 vs 57.32 us)
        Intent b = c.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
        if (b == null) return "unreadable:battery";
        int level = b.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
        int scale = b.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
        int status = b.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
        if (level < 0 || scale <= 0) return "unreadable:level/scale";
        if (status != BatteryManager.BATTERY_STATUS_CHARGING
                && status != BatteryManager.BATTERY_STATUS_FULL)
            return "not_charging:status=" + status;
        int pct = 100 * level / scale;
        // floor is overridable so the refusal path can be exercised: a gate
        // that never refuses proves nothing (A15)
        int floor = getInputData().getInt("battery_floor_pct", BATTERY_FLOOR_PCT);
        if (pct < floor) return "battery:" + pct + "%<" + floor + "%";

        long free = new StatFs(c.getFilesDir().getAbsolutePath()).getAvailableBytes();
        if (free < MIN_FREE_BYTES) return "space:" + (free >> 20) + "MB";
        return null;
    }

    @NonNull
    @Override
    public Result doWork() {
        String refuse = preflight();
        if (refuse != null) {
            // Result.retry() + BackoffPolicy.EXPONENTIAL 5 min == BOINC's
            // ANDROID_BATTERY_BACKOFF hysteresis, which its own comment calls crude
            Log.i(TAG, "PREFLIGHT REFUSED: " + refuse + " -> retry with backoff");
            return Result.retry();
        }
        // M1.7: the worker is now a FLEET MEMBER, not an adb puppet. It dials
        // the coordinator, pulls shards by CID, runs in-process, posts back.
        // Preflight is re-checked per job -- measured at 98.5 us in M1.1, so
        // per-job is viable and SCHEDULER_SPEC marks it required.
        int port = getInputData().getInt("port", 18080);
        Transport net = new Transport(port);
        String dir = getApplicationContext().getFilesDir().getAbsolutePath();
        java.io.File cache = new java.io.File(dir, "shards");
        cache.mkdirs();

        int done = 0, idle = 0;
        long t0 = System.nanoTime();
        while (idle < 2 && !isStopped()) {
            String refuse2 = preflight();          // per job, per SCHEDULER_SPEC
            if (refuse2 != null) {
                Log.i(TAG, "PREFLIGHT REFUSED mid-run: " + refuse2);
                return Result.retry();
            }
            String job = net.pollJob("android", 25000);
            if (job == null) { idle++; continue; }
            idle = 0;
            String cid = field(job, "shard_cid"), jid = field(job, "job_id");
            String fuel = field(job, "fuel");
            if (cid == null || jid == null) continue;

            java.io.File f = new java.io.File(cache, cid);
            if (!f.exists() || f.length() == 0) {
                byte[] d = net.fetchShard(cid);
                if (d == null) {                   // miss: do NOT fabricate a result
                    Log.i(TAG, "shard miss " + cid.substring(0, 12) + ", skipping");
                    continue;
                }
                try (java.io.FileOutputStream o = new java.io.FileOutputStream(f)) {
                    o.write(d);
                } catch (Exception e) { continue; }
            }
            String out;
            try {
                out = Metta.run(readFile(f), dir);
            } catch (Throwable e) {
                Log.i(TAG, "METTA FAILED on " + jid + ": " + e);
                continue;
            }
            String env = "{\"job_id\":\"" + jid + "\",\"worker\":\"android\","
                       + "\"shard_cid\":\"" + cid + "\",\"status\":\"OK\","
                       + "\"results\":\"" + out.trim().replace("\n", " | ").replace("\"", "'") + "\"}";
            if (net.postResult(env)) done++;
        }
        double ms = (System.nanoTime() - t0) / 1e6;
        Log.i(TAG, String.format("FLEET RUN: %d jobs in %.1f ms, exited on %s",
                done, ms, isStopped() ? "onStopped" : "idle"));
        return Result.success();
    }

    private static String field(String json, String key) {
        int i = json.indexOf("\"" + key + "\"");
        if (i < 0) return null;
        int c = json.indexOf(':', i);
        int a = json.indexOf('"', c + 1);
        if (a >= 0 && a < json.indexOf(',', c) + 1 || json.charAt(c + 1) == ' '
                && json.charAt(c + 2) == '"') {
            int b = json.indexOf('"', a + 1);
            return json.substring(a + 1, b);
        }
        int e = c + 1;
        while (e < json.length() && "0123456789 ".indexOf(json.charAt(e)) >= 0) e++;
        return json.substring(c + 1, e).trim();
    }

    private static String readFile(java.io.File f) throws Exception {
        byte[] b = new byte[(int) f.length()];
        try (java.io.FileInputStream in = new java.io.FileInputStream(f)) {
            int off = 0, n;
            while (off < b.length && (n = in.read(b, off, b.length - off)) > 0) off += n;
        }
        return new String(b, "UTF-8");
    }

    private void unusedTail() {
    }
}
