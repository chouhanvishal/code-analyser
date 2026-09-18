CC ?= gcc
CFLAGS ?= -std=c11 -Wall -Wextra -Isrc

.PHONY: test clean
test: build/test
	./build/test

build/test: src/strutil.c tests/test_strutil.c src/strutil.h
	mkdir -p build
	$(CC) $(CFLAGS) -o $@ src/strutil.c tests/test_strutil.c

clean:
	rm -rf build
