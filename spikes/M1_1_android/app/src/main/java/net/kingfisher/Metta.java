package net.kingfisher;

public final class Metta {
    static {
        System.loadLibrary("hyperonc");   // dependency first
        System.loadLibrary("kfjni");
    }
    /** Evaluate a MeTTa program in-process. Returns one result atom per line. */
    public static native String run(String program, String workingDir);
}
