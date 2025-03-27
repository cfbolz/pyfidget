#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <time.h>

enum func {
    func_varx,
    func_vary,
    func_varz,
    func_const,
    func_done,
    // unary functions
    func_abs,
    func_sqrt,
    func_square,
    func_neg,
    // binary functions
    func_add,
    func_sub,
    func_mul,
    func_min,
    func_max,
};

// tagged union
struct __attribute__((packed)) op {
    union {
        // constant
        float constant;
        // binary
        struct {
            uint16_t a0;
            uint16_t a1;
        } binary;
        // unary
        struct {
            uint16_t a0;
        } unary;
    };
    uint16_t destination;
    enum func f;
};

float __attribute__((regcall)) dispatch(struct op ops[], int pc, float values[], float x, float y);

#define MUSTTAIL __attribute__((musttail))

float values[65536];

float __attribute__((regcall)) execute_varx(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = x;
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_vary(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = y;
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_varz(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = 0;
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_const(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = ops[pc].constant;
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_abs(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = fabsf(values[ops[pc].unary.a0]);
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_sqrt(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = sqrtf(values[ops[pc].unary.a0]);
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_square(struct op ops[], int pc, float values[], float x, float y) {
    float arg = values[ops[pc].unary.a0];
    values[ops[pc].destination] = arg * arg;
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_neg(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = -values[ops[pc].unary.a0];
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_add(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = values[ops[pc].binary.a0] + values[ops[pc].binary.a1];
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_sub(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = values[ops[pc].binary.a0] - values[ops[pc].binary.a1];
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_mul(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = values[ops[pc].binary.a0] * values[ops[pc].binary.a1];
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_min(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = fminf(values[ops[pc].binary.a0], values[ops[pc].binary.a1]);
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_max(struct op ops[], int pc, float values[], float x, float y) {
    values[ops[pc].destination] = fmaxf(values[ops[pc].binary.a0], values[ops[pc].binary.a1]);
    MUSTTAIL return dispatch(ops, pc + 1, values, x, y);
}

float __attribute__((regcall)) execute_done(struct op ops[], int pc, float values[], float x, float y) {
    return values[ops[pc].unary.a0];
}

float __attribute__((regcall)) dispatch(struct op ops[], int pc, float values[], float x, float y) {
    enum func f = ops[pc].f;
    switch (f) {
        case func_varx:
            MUSTTAIL return execute_varx(ops, pc, values, x, y);
        case func_vary:
            MUSTTAIL return execute_vary(ops, pc, values, x, y);
        case func_varz:
            MUSTTAIL return execute_varz(ops, pc, values, x, y);
        case func_const:
            MUSTTAIL return execute_const(ops, pc, values, x, y);
        case func_abs:
            MUSTTAIL return execute_abs(ops, pc, values, x, y);
        case func_sqrt:
            MUSTTAIL return execute_sqrt(ops, pc, values, x, y);
        case func_square:
            MUSTTAIL return execute_square(ops, pc, values, x, y);
        case func_neg:
            MUSTTAIL return execute_neg(ops, pc, values, x, y);
        case func_add:
            MUSTTAIL return execute_add(ops, pc, values, x, y);
        case func_sub:
            MUSTTAIL return execute_sub(ops, pc, values, x, y);
        case func_mul:
            MUSTTAIL return execute_mul(ops, pc, values, x, y);
        case func_min:
            MUSTTAIL return execute_min(ops, pc, values, x, y);
        case func_max:
            MUSTTAIL return execute_max(ops, pc, values, x, y);
        case func_done:
            MUSTTAIL return execute_done(ops, pc, values, x, y);
        default:
            return NAN;
    }
}

void render_naive(struct op ops[], int height, uint8_t* pixels) {
    float minx = -1, maxx = 1, miny = -1, maxy = 1;
    for (int i = 0; i < height * height; i++) {
        int column_index = i % height;
        int row_index = i / height;
        float x = minx + (maxx - minx) / (float)(height - 1) * column_index;
        float y = miny + (maxy - miny) / (float)(height - 1) * row_index;
        // call dispatch
        float result = dispatch(ops, 0, values, x, y);
        // print the result with x and y
        // printf("%f %f %f\n", x, y, result);
        // printf("%f %f %f %i %i\n", x, y, result, i, result > 0.0? 255 : 0);
        // put newline if i % height == 0
        //if (i % height == 0) {
        //    putchar('|');
        //    putchar('\n');
        //}
        //putchar(result > 0.0 ? ' ' : '#');
        pixels[i] = result > 0 ? 255 : 0;
    }
}

uint16_t parse_arg(char* arg, char* names[], uint16_t count) {
    // parse the argument
    // it's always a name that must exist in the names list.
    // go through that list, compare the strings, return the index of said string
    for (uint16_t i = 0; i < count; i++) {
        int len = strlen(arg);
        if (arg[len - 1] == '\n') len--;
        if (strncmp(arg, names[i], len) == 0) {
            return i;
        }
    }
    fprintf(stderr, "Error: unknown argument %s\n", arg);
    exit(1);
}

enum func parse_operator_name(char* name) {
    // parse the operator name
    if (strncmp(name, "var-x", 5) == 0) {
        return func_varx;
    } else if (strncmp(name, "var-y", 5) == 0) {
        return func_vary;
    } else if (strncmp(name, "var-z", 5) == 0) {
        return func_varz;
    } else if (strncmp(name, "const", 5) == 0) {
        return func_const;
    } else if (strncmp(name, "abs", 3) == 0) {
        return func_abs;
    } else if (strncmp(name, "sqrt", 4) == 0) {
        return func_sqrt;
    } else if (strncmp(name, "square", 6) == 0) {
        return func_square;
    } else if (strncmp(name, "neg", 3) == 0) {
        return func_neg;
    } else if (strncmp(name, "add", 3) == 0) {
        return func_add;
    } else if (strncmp(name, "sub", 3) == 0) {
        return func_sub;
    } else if (strncmp(name, "mul", 3) == 0) {
        return func_mul;
    } else if (strncmp(name, "min", 3) == 0) {
        return func_min;
    } else if (strncmp(name, "max", 3) == 0) {
        return func_max;
    }
    fprintf(stderr, "Error: unknown operator %s\n", name);
    exit(1);
}

struct op parse_op(char* line, char* names[], uint16_t count) {
    // examples:
    // _0 const 2.95
    // _1 var-x
    // _2 const 8.13008
    // _3 mul _1 _2
    // _4 add _0 _3
    // _5 const 3.675
    // _6 add _5 _3
    // abc neg _6
    // now let's parse the line
    struct op op;
    char* tokname = strtok(line, " ");
    // copy tokname into a newly malloced string name
    char* name = malloc(strlen(tokname) + 1);
    strcpy(name, tokname);
    names[count] = name;
    if (name == NULL) {
        fprintf(stderr, "Error: empty line\n");
        exit(1);
    }
    // parse the operator
    char* operator = strtok(NULL, " ");
    op.f = parse_operator_name(operator);
    if (op.f == -1) {
        fprintf(stderr, "Error: unknown operator %s\n", operator);
        exit(1);
    }
    op.destination = count;
    // parse the arguments, depending on the operator
    switch (op.f) {
        case func_varx:
        case func_vary:
        case func_varz:
            // no arguments
            break;
        case func_const:{
            char* constant = strtok(NULL, " ");
            op.constant = atof(constant);
            break;}
        case func_abs:
        case func_sqrt:
        case func_square:
        case func_neg: {
            char* arg0 = strtok(NULL, " ");
            op.unary.a0 = parse_arg(arg0, names, count);
            break;}
        case func_add:
        case func_sub:
        case func_mul:
        case func_min:
        case func_max:{
            char* arg0 = strtok(NULL, " ");
            char* arg1 = strtok(NULL, " ");
            op.binary.a0 = parse_arg(arg0, names, count);
            op.binary.a1 = parse_arg(arg1, names, count);
            break;}
        case func_done:
            fprintf(stderr, "should be unreachable");
            exit(1);
    }
    return op;
}


struct op* parse(FILE *f) {
    // read the file and parse the ops
    // this is a stub, you need to implement the parsing logic
    struct op* ops = malloc(sizeof(struct op) * 65536);
    char* names[65536];
    size_t count = 0;
    char line[1024];
    while (fgets(line, sizeof(line), f)) {
        // skip comments
        if (line[0] == '#') {
            continue;
        }
        struct op op = parse_op(line, names, count);
        ops[count++] = op;
    }
    // terminate with a done op
    struct op done;
    done.f = func_done;
    done.destination = count;
    done.unary.a0 = count - 1;
    ops[count++] = done;
    // free the names array
    for (size_t i = 0; i < count; i++) {
        free(names[i]);
    }
    return ops;
}
int main(int argc, char *argv[]) {
    // open the first argument as a file
    FILE *f = fopen(argv[1], "rb");
    if (f == NULL) {
        perror("fopen");
        return 1;
    }
    // parse the ops
    struct op* ops = parse(f);
    // second commandline argument is the output file name
    char* output_file = argv[2];
    // third commandline argument is height and width
    int height = atoi(argv[3]);
    uint8_t* pixels = calloc(sizeof(uint8_t), height * height);
    //putchar('-');

    // time the execution or render_naive
    clock_t start = clock();
    render_naive(ops, height, pixels);
    clock_t end = clock();
    double elapsed = (double)(end - start) / CLOCKS_PER_SEC;
    printf("Elapsed time naive evaluation: %f seconds\n", elapsed);
    //putchar('\n');
    //putchar('-');
    // open the output file
    FILE *out = fopen(output_file, "wb");
    // write ppm
    fprintf(out, "P6\n%d %d\n255\n", height, height);
    // write the values
    for (int i = 0; i < height * height; i++) {
        fputc(pixels[i], out);
        fputc(pixels[i], out);
        fputc(pixels[i], out);
    }
    // close the output file
    fclose(out);
    // free the ops array
    free(ops);
    // close the file
    fclose(f);
    return 0;
}
