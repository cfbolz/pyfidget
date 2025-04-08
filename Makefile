all: c-pyfidget c-pyfidget-test

c-pyfidget-test: pyfidget/experiments.c
	clang -Wall pyfidget/experiments.c -lm -g3 -O0 -DPYFIDGETFUZZING=1 -mavx512f -o c-pyfidget-test

c-pyfidget: pyfidget/experiments.c
	clang -Wall pyfidget/experiments.c -lm -g3 -O3 -mavx512f -o c-pyfidget


clean:
	rm -f c-pyfidget c-pyfidget-test
