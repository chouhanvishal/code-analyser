package acceptance;

import roman.RomanNumerals;

public final class AcceptanceTest {
    public static void main(String[] args) {
        Check.eq("4", "IV", RomanNumerals.toRoman(4));
        Check.eq("9", "IX", RomanNumerals.toRoman(9));
        Check.eq("40", "XL", RomanNumerals.toRoman(40));
        Check.eq("3999", "MMMCMXCIX", RomanNumerals.toRoman(3999));
        Check.eq("from 3999", 3999, RomanNumerals.fromRoman("MMMCMXCIX"));
        Check.eq("from 444", 444, RomanNumerals.fromRoman("CDXLIV"));
        Check.throwsIAE("0", () -> RomanNumerals.toRoman(0));
        Check.throwsIAE("4000", () -> RomanNumerals.toRoman(4000));
        Check.throwsIAE("null", () -> RomanNumerals.fromRoman(null));
        Check.throwsIAE("empty", () -> RomanNumerals.fromRoman(""));
        Check.throwsIAE("lowercase", () -> RomanNumerals.fromRoman("iv"));
        Check.throwsIAE("unknown char", () -> RomanNumerals.fromRoman("IVA"));
        Check.throwsIAE("IIII", () -> RomanNumerals.fromRoman("IIII"));
        Check.throwsIAE("VX", () -> RomanNumerals.fromRoman("VX"));
        Check.throwsIAE("IM", () -> RomanNumerals.fromRoman("IM"));
        boolean roundTrip = true;
        for (int n = 1; n <= 3999; n++) {
            if (RomanNumerals.fromRoman(RomanNumerals.toRoman(n)) != n) { roundTrip = false; break; }
        }
        Check.eq("round trip 1..3999", true, roundTrip);
        Check.finish();
    }
}
