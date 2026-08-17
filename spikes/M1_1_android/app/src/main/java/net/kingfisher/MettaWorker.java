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
        String prog = getInputData().getString("program");
        if (prog == null) prog = "!(+ 1 2)\n";

        // PORT_PLAN M1.3: a fresh process per job is a hard requirement
        // (S60/A8 atomspace pollution; process-global NEXT_VARIABLE_ID).
        // NOT satisfied here -- WorkManager reuses the app process. Logged.
        long t0 = System.nanoTime();
        String out;
        try {
            out = Metta.run(prog, getApplicationContext().getFilesDir().getAbsolutePath());
        } catch (Throwable e) {
            Log.i(TAG, "METTA FAILED: " + e);
            return Result.failure();
        }
        double ms = (System.nanoTime() - t0) / 1e6;

        if (isStopped()) {                    // onStopped(): constraints went false
            Log.i(TAG, "STOPPED mid-job; no checkpoint exists (S68) -> retry whole job");
            return Result.retry();
        }
        Log.i(TAG, String.format("JOB OK in %.2f ms, results=[%s]",
                ms, out.trim().replace("\n", " | ")));
        return Result.success();
    }
}
