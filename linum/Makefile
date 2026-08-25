CC = gcc
CFLAGS = -O3 -march=goldmont-plus -msse4.2 -Wall

all: minwm mhttpsd mgrep msniff mgen

minwm: src/minwm.c
	$(CC) $(CFLAGS) src/minwm.c -o bin/minwm -lX11

mhttpsd: src/mhttpsd.c
	$(CC) $(CFLAGS) src/mhttpsd.c -o bin/mhttpsd

mgrep: src/mgrep.c
	$(CC) $(CFLAGS) -pthread src/mgrep.c -o bin/mgrep

msniff: src/msniff.c
	$(CC) $(CFLAGS) src/msniff.c -o bin/msniff

mgen: src/mgen.c
	$(CC) $(CFLAGS) src/mgen.c -o bin/mgen

package: all
	mkdir -p dist/linum/bin dist/linum/src
	cp bin/minwm bin/mhttpsd bin/mgrep bin/msniff bin/mgen dist/linum/bin/
	cp src/*.c dist/linum/src/ 2>/dev/null || true
	cp Makefile dist/linum/
	tar -czf linum-stack.tar.gz -C dist linum
	rm -rf dist
	@echo "Successfully packaged Linum stack into linum-stack.tar.gz"

clean:
	rm -rf bin/* linum-stack.tar.gz
