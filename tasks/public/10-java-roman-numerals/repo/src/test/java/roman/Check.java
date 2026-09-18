package roman;

final class Check {
    static int failures = 0;
    static void eq(String desc, Object want, Object got) {
        if (want.equals(got)) System.out.println("ok   " + desc);
        else { System.out.println("FAIL " + desc + ": want " + want + " got " + got); failures++; }
    }
    static void throwsIAE(String desc, Runnable r) {
        try { r.run(); System.out.println("FAIL " + desc + ": no exception"); failures++; }
        catch (IllegalArgumentException e) { System.out.println("ok   " + desc); }
    }
    static void finish() {
        if (failures > 0) { System.out.println(failures + " failure(s)"); System.exit(1); }
        System.out.println("all passed");
    }
}
