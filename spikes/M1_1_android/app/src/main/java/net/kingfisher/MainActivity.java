package net.kingfisher;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.os.Bundle;
import android.os.PowerManager;
import android.os.StatFs;
import android.util.Log;
import androidx.work.BackoffPolicy;
import androidx.work.Constraints;
import androidx.work.Data;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.WorkManager;
import java.util.concurrent.TimeUnit;

/**
 * M1.1 -- the honest preflight number.
 *
 * M1.3 measured preflight at 35.1 ms and concluded per-job preflight was not
 * viable. That was `adb shell` + `dumpsys` text parsing over USB: the harness,
 * not the mechanism (A18). SCHEDULER_SPEC:19-20 specifies these in-process
 * calls instead. This measures them.
 */
public class MainActivity extends Activity {
    static final String TAG = "KFPREFLIGHT";

    interface Block { void run(); }

    private double bench(String label, int reps, Block b) {
        for (int i = 0; i < reps / 10 + 1; i++) b.run();      // warm
        long t0 = System.nanoTime();
        for (int i = 0; i < reps; i++) b.run();
        double us = (System.nanoTime() - t0) / 1000.0 / reps;
        Log.i(TAG, String.format("BENCH %-34s %10.2f us", label, us));
        return us;
    }

    @Override
    protected void onCreate(Bundle s) {
        super.onCreate(s);

        String soLoad;
        try {
            long t0 = System.nanoTime();
            System.loadLibrary("hyperonc");
            soLoad = "OK " + (System.nanoTime() - t0) / 1e6 + " ms";
        } catch (Throwable e) {
            soLoad = "FAILED: " + e.getMessage();
        }
        Log.i(TAG, "libhyperonc.so load: " + soLoad);

        final PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        final BatteryManager bm = (BatteryManager) getSystemService(Context.BATTERY_SERVICE);

        Log.i(TAG, "thermalStatus=" + pm.getCurrentThermalStatus()
                 + " capacity=" + bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) + "%");

        final String dir = getFilesDir().getAbsolutePath();
        int n = 2000;
        double thermal = bench("getCurrentThermalStatus()", n, () -> pm.getCurrentThermalStatus());
        double cap = bench("BATTERY_PROPERTY_CAPACITY", n,
                () -> bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY));
        double sticky = bench("ACTION_BATTERY_CHANGED sticky", 200,
                () -> registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED)));
        double space = bench("StatFs availableBytes", n,
                () -> new StatFs(dir).getAvailableBytes());

        // the gate S6 mandates inside doWork(): thermal + charge floor + space
        double total = bench("FULL PREFLIGHT (spec path)", n, () -> {
            pm.getCurrentThermalStatus();
            bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
            new StatFs(dir).getAvailableBytes();
        });

        Log.i(TAG, String.format(
            "SUMMARY thermal=%.2f cap=%.2f sticky=%.2f space=%.2f full=%.2f us"
            + " | adb+dumpsys was 35100 us -> %.0fx | vs 68.8 ms job = %.6fx",
            thermal, cap, sticky, space, total, 35100.0 / total, total / 68800.0));
        // ---- run MeTTa in-process and report the result atoms
        try {
            String prog = "!(+ 1 2)\n!(if (> 3 2) yes no)\n"
                        + "!(intersection-atom (A B C) (B C D))\n";
            long t0 = System.nanoTime();
            String out = Metta.run(prog, getFilesDir().getAbsolutePath());
            double ms = (System.nanoTime() - t0) / 1e6;
            Log.i(TAG, String.format("METTA in-process OK in %.2f ms", ms));
            for (String line : out.split("\n")) {
                if (!line.isEmpty()) Log.i(TAG, "METTA RESULT| " + line);
            }
        } catch (Throwable e) {
            Log.i(TAG, "METTA FAILED: " + e);
        }
        // ---- M1.3: the five declarative constraints, enqueued for real
        Constraints spec = new Constraints.Builder()
                .setRequiresCharging(true)                              // rule 1
                .setRequiresDeviceIdle(true)                            // rule 5
                .setRequiredNetworkType(NetworkType.UNMETERED)          // rule 6
                .setRequiresBatteryNotLow(true)                         // rule 2 (partial)
                .setRequiresStorageNotLow(true)
                .build();
        // An Android app does NOT inherit the shell environment from `am start`,
        // so the token arrives as an intent extra:
        //   am start -n net.kingfisher/.MainActivity --es token <tok>
        String kfTok = getIntent() == null ? null : getIntent().getStringExtra("token");
        Data in = new Data.Builder()
                .putString("token", kfTok == null ? "" : kfTok)
                .putString("program",
                "!(+ 1 2)\n!(intersection-atom (A B C) (B C D))\n").build();

        WorkManager wm = WorkManager.getInstance(this);
        wm.enqueueUniqueWork("kf-spec", ExistingWorkPolicy.REPLACE,
                new OneTimeWorkRequest.Builder(MettaWorker.class)
                        .setConstraints(spec).setInputData(in)
                        // NO setBackoffCriteria here. SCHEDULER_SPEC 2 specifies
                        // rule 4 (EXPONENTIAL, 5 min) and rule 5 (requiresDeviceIdle)
                        // in the same builder; WorkManager throws
                        // "Cannot set backoff criteria on an idle mode job".
                        // The spec as written does not build. Rules 4 and 5 are
                        // mutually exclusive and one must be dropped.
                        .addTag("kf-spec").build());
        Log.i(TAG, "enqueued kf-spec: 5 constraints, NO backoff (rules 4+5 are exclusive)");

        // A second request WITHOUT requiresDeviceIdle, so the worker body is
        // actually observed. S6 warns idle can starve on a phone that is never
        // idle-while-charging; without this the run would prove nothing.
        wm.enqueueUniqueWork("kf-now", ExistingWorkPolicy.REPLACE,
                new OneTimeWorkRequest.Builder(MettaWorker.class)
                        .setConstraints(new Constraints.Builder()
                                .setRequiresCharging(true)
                                .setRequiredNetworkType(NetworkType.UNMETERED).build())
                        .setInputData(in)
                        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 5, TimeUnit.MINUTES)
                        .addTag("kf-now").build());
        Log.i(TAG, "enqueued kf-now without idle constraint");

        // positive control: an unsatisfiable floor must produce Result.retry()
        wm.enqueueUniqueWork("kf-refuse", ExistingWorkPolicy.REPLACE,
                new OneTimeWorkRequest.Builder(MettaWorker.class)
                        .setConstraints(new Constraints.Builder()
                                .setRequiresCharging(true).build())
                        .setInputData(new Data.Builder()
                                .putString("program", "!(+ 1 2)\n")
                                .putInt("battery_floor_pct", 101).build())
                        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 5, TimeUnit.MINUTES)
                        .addTag("kf-refuse").build());
        Log.i(TAG, "enqueued kf-refuse with an unsatisfiable 101% floor");
        Soak.run(getFilesDir().getAbsolutePath());
        Log.i(TAG, "DONE");
    }
}
