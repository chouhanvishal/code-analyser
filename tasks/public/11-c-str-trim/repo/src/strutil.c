#include <string.h>
#include "strutil.h"

char *str_trim(const char *s, char *out, size_t outsz) {
    while (*s == ' ') {
        s++;
    }
    size_t n = strlen(s);
    if (n >= outsz) {
        n = outsz - 1;
    }
    memcpy(out, s, n);
    out[n] = '\0';
    return out;
}
