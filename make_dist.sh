#!/bin/sh
set -e

DIST_DIR="dist"
rm -rf "$DIST_DIR"
mkdir -p "$DIST_DIR"

echo "[*] Generating C source from R2 compiler..."
python3 src/cli/r2c.py proofboot_pb010.r2 --emit-c -o "$DIST_DIR/proofboot_pb010.c"

cat <<'HEADER' > "$DIST_DIR/proofboot_pb010.h"
#ifndef PROOFBOOT_PB010_H
#define PROOFBOOT_PB010_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

uint32_t crc32(uint32_t buffer, uint32_t len);
uint32_t constant_time_eq(uint32_t a, uint32_t b, uint32_t len);
uint32_t parse_header(uint32_t slot_base);
uint32_t arbitrate_active_header(uint32_t dev);
uint32_t commit_transition(uint32_t dev, uint32_t new_payload, uint32_t payload_len, uint32_t new_generation);

#ifdef __cplusplus
}
#endif

#endif /* PROOFBOOT_PB010_H */
HEADER

cp harness.c "$DIST_DIR/test_runner.c"

cat <<'MAKE' > "$DIST_DIR/Makefile"
CC ?= clang
CFLAGS ?= -std=c99 -Wall -Wextra -O2

all: libproofboot.a proofboot_runner

proofboot_pb010.o: proofboot_pb010.c
	$(CC) $(CFLAGS) -c proofboot_pb010.c -o proofboot_pb010.o

libproofboot.a: proofboot_pb010.o
	ar rcs libproofboot.a proofboot_pb010.o

proofboot_runner: test_runner.c proofboot_pb010.o
	$(CC) $(CFLAGS) test_runner.c proofboot_pb010.o -o proofboot_runner

test: proofboot_runner
	./proofboot_runner

clean:
	rm -f *.o *.a proofboot_runner
MAKE

echo "[OK] Distribution bundle created in dist/:"
ls -la "$DIST_DIR"
