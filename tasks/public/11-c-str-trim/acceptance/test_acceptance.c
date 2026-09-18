#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "strutil.h"

static int failures = 0;
#define EXPECT_STR(desc, want, got) do { \
    const char *g_ = (got); \
    if (g_ && strcmp(want, g_) == 0) printf("ok   %s\n", desc); \
    else { printf("FAIL %s: want '%s' got '%s'\n", desc, want, g_ ? g_ : "(null)"); failures++; } \
} while (0)

int main(void) {
    char buf[8];
    EXPECT_STR("leading spaces", "hello", str_trim("   hello", buf, sizeof buf));
    EXPECT_STR("trailing spaces", "hello", str_trim("hello   ", buf, sizeof buf));
    EXPECT_STR("tabs and newlines", "hi", str_trim("\t\n hi \r\n", buf, sizeof buf));
    EXPECT_STR("inner whitespace kept", "a b", str_trim("  a b  ", buf, sizeof buf));
    EXPECT_STR("all whitespace", "", str_trim("   \t ", buf, sizeof buf));
    EXPECT_STR("empty", "", str_trim("", buf, sizeof buf));
    EXPECT_STR("truncation", "abcdefg", str_trim("  abcdefghij  ", buf, sizeof buf));
    char one[1];
    EXPECT_STR("outsz 1 gives empty", "", str_trim("xyz", one, 1));
    if (str_trim("xyz", buf, 0) == NULL) printf("ok   outsz 0 returns NULL\n");
    else { printf("FAIL outsz 0 must return NULL\n"); failures++; }
    if (failures) { printf("%d failure(s)\n", failures); return 1; }
    puts("all passed");
    return 0;
}
