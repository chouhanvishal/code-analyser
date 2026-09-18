#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "strutil.h"

int main(void) {
    char buf[32];
    assert(strcmp(str_trim("  hello", buf, sizeof buf), "hello") == 0);
    assert(strcmp(str_trim("hello  ", buf, sizeof buf), "hello") == 0);
    puts("all passed");
    return 0;
}
