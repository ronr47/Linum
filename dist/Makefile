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
