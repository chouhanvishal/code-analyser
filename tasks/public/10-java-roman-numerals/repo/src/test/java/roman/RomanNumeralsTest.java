package roman;

public final class RomanNumeralsTest {
    public static void main(String[] args) {
        Check.eq("1", "I", RomanNumerals.toRoman(1));
        Check.eq("1994", "MCMXCIV", RomanNumerals.toRoman(1994));
        Check.eq("round trip 58", 58, RomanNumerals.fromRoman("LVIII"));
        Check.finish();
    }
}
