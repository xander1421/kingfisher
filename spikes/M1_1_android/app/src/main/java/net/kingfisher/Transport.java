package net.kingfisher;

import android.util.Log;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * M1.7 dial-out transport, device side. Every call is outbound.
 *
 * S8: the DAS bus dials clients back and a phone cannot accept that. So the
 * device long-polls for work, pulls shards by CID, and posts envelopes. It
 * never listens on a port, which also means the app needs no inbound
 * permission and no stable address.
 *
 * The coordinator is on the host loopback, reached through
 * `adb reverse tcp:PORT tcp:PORT`. Nothing here touches a real network.
 */
public final class Transport {
    static final String TAG = "KFNET";
    private final String base;

    public Transport(int port) { this.base = "http://127.0.0.1:" + port; }

    private static byte[] readAll(InputStream in) throws Exception {
        ByteArrayOutputStream o = new ByteArrayOutputStream();
        byte[] b = new byte[8192];
        int n;
        while ((n = in.read(b)) > 0) o.write(b, 0, n);
        return o.toByteArray();
    }

    /** Distinct from null: the poll FAILED, which is not the same as no work. */
    public static final String ERROR = "\u0000ERR";

    /** @return job JSON, null on 204 (no work), or ERROR on a transport fault.
     *  Conflating the last two made the worker exit after two instant network
     *  errors, reporting "exited on idle" in 15.8 ms. */
    public String pollJob(String worker, int timeoutMs) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(base + "/job?worker=" + worker).openConnection();
            c.setConnectTimeout(5000);
            // do not reuse pooled sockets across long-polls
            c.setRequestProperty("Connection", "close");
            c.setReadTimeout(timeoutMs);
            int code = c.getResponseCode();
            if (code != 200) { Log.i(TAG, "poll HTTP " + code); return ERROR; }
            String b = new String(readAll(c.getInputStream()), "UTF-8").trim();
            // empty body == no work. The server does not use 204: okhttp throws
            // "unexpected end of stream" on one.
            return b.isEmpty() ? null : b;
        } catch (Exception e) {
            Log.i(TAG, "poll failed: " + e);
            return ERROR;
        } finally { if (c != null) c.disconnect(); }
    }

    /**
     * @return shard bytes, or null. A non-200 MUST return null rather than the
     * error body: M1.7's shell agent used `curl -s` without `-f`, wrote the
     * empty 404 body to the cache, ran MeTTa on an empty file and posted the
     * result. Checking the status code is the whole fix.
     */
    public byte[] fetchShard(String cid) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(base + "/shard/" + cid).openConnection();
            c.setConnectTimeout(5000);
            // do not reuse pooled sockets across long-polls
            c.setRequestProperty("Connection", "close");
            c.setReadTimeout(60000);
            if (c.getResponseCode() != 200) {
                Log.i(TAG, "shard " + cid.substring(0, 12) + " HTTP " + c.getResponseCode());
                return null;
            }
            byte[] d = readAll(c.getInputStream());
            return d.length == 0 ? null : d;
        } catch (Exception e) {
            Log.i(TAG, "fetch failed: " + e);
            return null;
        } finally { if (c != null) c.disconnect(); }
    }

    public boolean postResult(String json) {
        HttpURLConnection c = null;
        try {
            c = (HttpURLConnection) new URL(base + "/result").openConnection();
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setConnectTimeout(5000);
            // do not reuse pooled sockets across long-polls
            c.setRequestProperty("Connection", "close");
            c.setReadTimeout(30000);
            c.setRequestProperty("Content-Type", "application/json");
            byte[] b = json.getBytes("UTF-8");
            c.setFixedLengthStreamingMode(b.length);
            OutputStream o = c.getOutputStream();
            o.write(b);
            o.close();
            return c.getResponseCode() == 200;
        } catch (Exception e) {
            Log.i(TAG, "post failed: " + e);
            return false;
        } finally { if (c != null) c.disconnect(); }
    }
}
