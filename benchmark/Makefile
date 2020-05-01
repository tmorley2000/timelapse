
all: libfunpack.so

libfunpack.so: fastunpack.o
	gcc -shared -o libfunpack.so fastunpack.o

fastunpack.o:
	gcc -O2 -falign-functions=16 -falign-loops=16 fastunpack.c -c

clean:
	rm fastunpack.o libfunpack.so


