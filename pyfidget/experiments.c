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
struct op {
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
    //uint16_t destination;
    enum func f;
};

#define MUSTTAIL __attribute__((musttail))
#define REGCALL __attribute__((regcall))
//#define REGCALL 

float REGCALL dispatch(struct op ops[], int pc, float x, float y);


float values[65536];

float REGCALL execute_varx(struct op ops[], int pc, float x, float y) {
    values[pc] = x;
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_vary(struct op ops[], int pc, float x, float y) {
    values[pc] = y;
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_varz(struct op ops[], int pc, float x, float y) {
    values[pc] = 0;
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_const(struct op ops[], int pc, float x, float y) {
    values[pc] = ops[pc].constant;
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_abs(struct op ops[], int pc, float x, float y) {
    values[pc] = fabsf(values[ops[pc].unary.a0]);
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_sqrt(struct op ops[], int pc, float x, float y) {
    values[pc] = sqrtf(values[ops[pc].unary.a0]);
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_square(struct op ops[], int pc, float x, float y) {
    float arg = values[ops[pc].unary.a0];
    values[pc] = arg * arg;
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_neg(struct op ops[], int pc, float x, float y) {
    values[pc] = -values[ops[pc].unary.a0];
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_add(struct op ops[], int pc, float x, float y) {
    values[pc] = values[ops[pc].binary.a0] + values[ops[pc].binary.a1];
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_sub(struct op ops[], int pc, float x, float y) {
    values[pc] = values[ops[pc].binary.a0] - values[ops[pc].binary.a1];
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_mul(struct op ops[], int pc, float x, float y) {
    values[pc] = values[ops[pc].binary.a0] * values[ops[pc].binary.a1];
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_min(struct op ops[], int pc, float x, float y) {
    values[pc] = fminf(values[ops[pc].binary.a0], values[ops[pc].binary.a1]);
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_max(struct op ops[], int pc, float x, float y) {
    values[pc] = fmaxf(values[ops[pc].binary.a0], values[ops[pc].binary.a1]);
    MUSTTAIL return dispatch(ops, pc + 1, x, y);
}

float REGCALL execute_done(struct op ops[], int pc, float x, float y) {
    return values[ops[pc].unary.a0];
}

float REGCALL dispatch(struct op ops[], int pc, float x, float y) {
    enum func f = ops[pc].f;
    switch (f) {
        case func_varx:
            MUSTTAIL return execute_varx(ops, pc, x, y);
        case func_vary:
            MUSTTAIL return execute_vary(ops, pc, x, y);
        case func_varz:
            MUSTTAIL return execute_varz(ops, pc, x, y);
        case func_const:
            MUSTTAIL return execute_const(ops, pc, x, y);
        case func_abs:
            MUSTTAIL return execute_abs(ops, pc, x, y);
        case func_sqrt:
            MUSTTAIL return execute_sqrt(ops, pc, x, y);
        case func_square:
            MUSTTAIL return execute_square(ops, pc, x, y);
        case func_neg:
            MUSTTAIL return execute_neg(ops, pc, x, y);
        case func_add:
            MUSTTAIL return execute_add(ops, pc, x, y);
        case func_sub:
            MUSTTAIL return execute_sub(ops, pc, x, y);
        case func_mul:
            MUSTTAIL return execute_mul(ops, pc, x, y);
        case func_min:
            MUSTTAIL return execute_min(ops, pc, x, y);
        case func_max:
            MUSTTAIL return execute_max(ops, pc, x, y);
        case func_done:
            MUSTTAIL return execute_done(ops, pc, x, y);
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
        float result = dispatch(ops, 0, x, y);
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

// optimizing

struct interval {
    float min;
    float max;
};

struct optimizer {
    struct op* ops;
    struct op* resultops;
    uint16_t count;
    struct interval* intervals;
    uint16_t* opreplacements;
    float minx;
    float maxx;
    float miny;
    float maxy;
};

struct optimizer* create_optimizer(struct op* ops) {
    struct optimizer* opt = malloc(sizeof(struct optimizer));
    opt->ops = ops;
    opt->resultops = malloc(sizeof(struct op) * 65536);
    opt->count = 0;
    opt->intervals = malloc(sizeof(struct interval) * 65536);
    opt->opreplacements = calloc(sizeof(uint16_t), 65536);
    return opt;
}

void destroy_optimizer(struct optimizer* opt) {
    free(opt->resultops);
    free(opt->intervals);
    free(opt->opreplacements);
    free(opt);
}

uint16_t opt_default(struct op newop, struct optimizer* opt, struct interval interval) {
    opt->resultops[opt->count] = newop;
    opt->intervals[opt->count] = interval;
    return opt->count++;
}

uint16_t opt_default0(enum func f, struct optimizer* opt, struct interval interval) {
    struct op newop;
    newop.f = f;
    return opt_default(newop, opt, interval);
}

uint16_t opt_default1(enum func f, struct optimizer* opt, struct interval interval, uint16_t arg0) {
    struct op newop;
    newop.f = f;
    newop.unary.a0 = arg0;
    return opt_default(newop, opt, interval);
}

uint16_t opt_default2(enum func f, struct optimizer* opt, struct interval interval, uint16_t arg0, uint16_t arg1) {
    struct op newop;
    newop.f = f;
    newop.binary.a0 = arg0;
    newop.binary.a1 = arg1;
    return opt_default(newop, opt, interval);
}

uint16_t opt_newconst(struct optimizer* opt, float constant) {
    struct op newop;
    newop.f = func_const;
    newop.constant = constant;
    opt->resultops[opt->count] = newop;
    struct interval newinterval;
    newinterval.min = constant;
    newinterval.max = constant;
    opt->intervals[opt->count] = newinterval;
    return opt->count++;
}

uint16_t opt_varx(struct op op, struct optimizer* opt) {
    struct interval interval = {.min=opt->minx, .max=opt->maxx};
    return opt_default0(func_varx, opt, interval);
}

uint16_t opt_vary(struct op op, struct optimizer* opt) {
    struct interval interval = {.min=opt->miny, .max=opt->maxy};
    return opt_default0(func_vary, opt, interval);
}

uint16_t opt_varz(struct op op, struct optimizer* opt) {
    struct interval interval = {.min=0, .max=0};
    return opt_default0(func_varz, opt, interval);
}
uint16_t opt_const(struct op op, struct optimizer* opt) {
    return opt_newconst(opt, op.constant);
}

uint16_t opt_neg(struct op op, struct optimizer* opt, uint16_t arg0, struct interval a0interval) {
    struct interval resinterval;
    resinterval.min = -a0interval.max;
    resinterval.max = -a0interval.min;
    // simplify neg of neg
    struct op arg0op = opt->resultops[arg0];
    if (arg0op.f == func_neg) {
        // remove the neg
        return opt_default1(func_neg, opt, a0interval, arg0op.unary.a0);
    }
    return opt_default1(func_neg, opt, resinterval, arg0);
}

uint16_t opt_abs(struct op op, struct optimizer* opt, uint16_t arg0, struct interval a0interval) {
    if (a0interval.min >= 0) {
        return arg0;
    }
    if (a0interval.max <= 0) {
        return opt_neg(op, opt, arg0, a0interval);
    }
    struct op arg0op = opt->resultops[arg0];
    if (arg0op.f == func_neg) {
        struct interval arg0arg0interval = opt->intervals[arg0op.unary.a0];
        return opt_abs(op, opt, arg0op.unary.a0, arg0arg0interval);
    }
    struct interval resinterval;
    resinterval.min = 0.0;
    resinterval.max = fmaxf(-a0interval.min, a0interval.max);
    return opt_default1(func_abs, opt, resinterval, arg0);
}

uint16_t opt_sqrt(struct op op, struct optimizer* opt, uint16_t arg0, struct interval a0interval) {
    struct interval resinterval;
    if (a0interval.min < 0) {
        resinterval.max = NAN;
        resinterval.min = NAN;
    } else {
        resinterval.min = sqrtf(a0interval.min);
        resinterval.max = sqrtf(a0interval.max);
    }
    return opt_default1(func_sqrt, opt, resinterval, arg0);
}

uint16_t opt_square(struct op op, struct optimizer* opt, uint16_t arg0, struct interval a0interval) {
    struct interval resinterval;
    if (a0interval.min >= 0) {
        resinterval.min = a0interval.min * a0interval.min;
        resinterval.max = a0interval.max * a0interval.max;
    } else if (a0interval.max <= 0) {
        resinterval.min = a0interval.max * a0interval.max;
        resinterval.max = a0interval.min * a0interval.min;
    } else {
        resinterval.min = 0.0;
        resinterval.max = fmaxf(a0interval.min * a0interval.min, a0interval.max * a0interval.max);
    }
    // if the argument of the square is a neg operation, we can remove the neg
    struct op arg0op = opt->resultops[arg0];
    if (arg0op.f == func_neg) {
        // remove the neg
        return opt_default1(func_square, opt, resinterval, arg0op.unary.a0);
    }
    return opt_default1(func_square, opt, resinterval, arg0);
}

uint16_t opt_min(struct op op, struct optimizer* opt, uint16_t arg0, uint16_t arg1, struct interval a0interval, struct interval a1interval) {
    if (a0interval.max < a1interval.min) {
        return arg0;
    }
    if (a1interval.max < a0interval.min) {
        return arg1;
    }
    if (arg0 == arg1) {
        return arg0;
    }
    struct op arg0op = opt->resultops[arg0];
    if (arg0op.f == func_min) {
        // min(min(a, b), a) = min(a, b)
        if (arg0op.binary.a0 == arg1 && arg0op.binary.a1 == arg1) {
            return arg0;
        }
    }
    struct op arg1op = opt->resultops[arg1];
    if (arg1op.f == func_min) {
        // min(a, min(a, b)) = min(a, b)
        if (arg1op.binary.a0 == arg1 && arg1op.binary.a1 == arg1) {
            return arg1;
        }
    }
    struct interval resinterval;
    resinterval.min = fminf(a0interval.min, a1interval.min);
    resinterval.max = fminf(a0interval.max, a1interval.max);
    return opt_default2(func_min, opt, resinterval, arg0, arg1);
}

uint16_t opt_max(struct op op, struct optimizer* opt, uint16_t arg0, uint16_t arg1, struct interval a0interval, struct interval a1interval) {
    if (a0interval.min > a1interval.max) {
        return arg0;
    }
    if (a1interval.min > a0interval.max) {
        return arg1;
    }
    if (arg0 == arg1) {
        return arg0;
    }
    struct op arg0op = opt->resultops[arg0];
    if (arg0op.f == func_max) {
        // max(max(a, b), a) = max(a, b)
        if (arg0op.binary.a0 == arg1 && arg0op.binary.a1 == arg1) {
            return arg0;
        }
    }
    struct op arg1op = opt->resultops[arg1];
    if (arg1op.f == func_max) {
        // max(a, max(a, b)) = max(a, b)
        if (arg1op.binary.a0 == arg1 && arg1op.binary.a1 == arg1) {
            return arg1;
        }
    }
    struct interval resinterval;
    resinterval.min = fmaxf(a0interval.min, a1interval.min);
    resinterval.max = fmaxf(a0interval.max, a1interval.max);
    return opt_default2(func_max, opt, resinterval, arg0, arg1);
}

uint16_t opt_mul(struct op op, struct optimizer* opt, uint16_t arg0, uint16_t arg1, struct interval a0interval, struct interval a1interval) {
    if (a0interval.min == a0interval.max) {
        if (a0interval.min == 0) {
            return opt_newconst(opt, 0);
        }
        if (a0interval.min == 1) {
            return arg1;
        }
        if (a0interval.min == -1) {
            return opt_neg(op, opt, arg1, a1interval);
        }
    }
    if (a1interval.min == a1interval.max) {
        if (a1interval.min == 0) {
            return opt_newconst(opt, 0);
        }
        if (a1interval.min == 1) {
            return arg0;
        }
        if (a1interval.min == -1) {
            return opt_neg(op, opt, arg0, a0interval);
        }
    }
    struct interval resinterval;
    resinterval.min = fminf(fminf(a0interval.min * a1interval.min, a0interval.min * a1interval.max), fminf(a0interval.max * a1interval.min, a0interval.max * a1interval.max));
    resinterval.max = fmaxf(fmaxf(a0interval.min * a1interval.min, a0interval.min * a1interval.max), fmaxf(a0interval.max * a1interval.min, a0interval.max * a1interval.max));
    return opt_default2(func_mul, opt, resinterval, arg0, arg1);
}

uint16_t opt_sub(struct op op, struct optimizer* opt, uint16_t arg0, uint16_t arg1, struct interval a0interval, struct interval a1interval) {
    if (arg0 == arg1) {
        return opt_newconst(opt, 0);
    }
    if (a0interval.min == a0interval.max) {
        if (a0interval.min == 0) {
            return opt_neg(op, opt, arg1, a1interval);
        }
    }
    if (a1interval.min == a1interval.max) {
        if (a1interval.min == 0) {
            return arg0;
        }
    }
    struct interval resinterval;
    resinterval.min = a0interval.min - a1interval.max;
    resinterval.max = a0interval.max - a1interval.min;
    return opt_default2(func_sub, opt, resinterval, arg0, arg1);
}

uint16_t opt_add(struct op op, struct optimizer* opt, uint16_t arg0, uint16_t arg1, struct interval a0interval, struct interval a1interval) {
    if (a0interval.min == a0interval.max) {
        if (a0interval.min == 0) {
            return arg1;
        }
    }
    if (a1interval.min == a1interval.max) {
        if (a1interval.min == 0) {
            return arg0;
        }
    }
    struct interval resinterval;
    resinterval.min = a0interval.min + a1interval.min;
    resinterval.max = a0interval.max + a1interval.max;
    return opt_default2(func_add, opt, resinterval, arg0, arg1);
}

uint16_t opt_done(struct op op, struct optimizer* opt, uint16_t arg0, struct interval a0interval) {
    return opt_default1(func_done, opt, a0interval, arg0);
}

uint16_t opt_op(struct op op, struct optimizer* opt) {
    uint16_t a0, a1;
    struct interval a0interval;
    struct interval a1interval;
    switch(op.f) {
        case func_varx:
            return opt_varx(op, opt);
        case func_vary:
            return opt_vary(op, opt);
        case func_varz:
            return opt_varz(op, opt);
        case func_const:
            return opt_const(op, opt);
        case func_abs:
            a0 = opt->opreplacements[op.unary.a0];
            a0interval = opt->intervals[a0];
            return opt_abs(op, opt, a0, a0interval);
        case func_sqrt:
            a0 = opt->opreplacements[op.unary.a0];
            a0interval = opt->intervals[a0];
            return opt_sqrt(op, opt, a0, a0interval);
        case func_square: 
            a0 = opt->opreplacements[op.unary.a0];
            a0interval = opt->intervals[a0];
            return opt_square(op, opt, a0, a0interval);
        case func_neg:
            a0 = opt->opreplacements[op.unary.a0];
            a0interval = opt->intervals[a0];
            return opt_neg(op, opt, a0, a0interval);
        case func_add:
            a0 = opt->opreplacements[op.binary.a0];
            a1 = opt->opreplacements[op.binary.a1];
            a0interval = opt->intervals[a0];
            a1interval = opt->intervals[a1];
            return opt_add(op, opt, a0, a1, a0interval, a1interval);
        case func_sub:
            a0 = opt->opreplacements[op.binary.a0];
            a1 = opt->opreplacements[op.binary.a1];
            a0interval = opt->intervals[a0];
            a1interval = opt->intervals[a1];
            return opt_sub(op, opt, a0, a1, a0interval, a1interval);
        case func_mul:
            a0 = opt->opreplacements[op.binary.a0];
            a1 = opt->opreplacements[op.binary.a1];
            a0interval = opt->intervals[a0];
            a1interval = opt->intervals[a1];
            return opt_mul(op, opt, a0, a1, a0interval, a1interval);
        case func_min:
            a0 = opt->opreplacements[op.binary.a0];
            a1 = opt->opreplacements[op.binary.a1];
            a0interval = opt->intervals[a0];
            a1interval = opt->intervals[a1];
            return opt_min(op, opt, a0, a1, a0interval, a1interval);
        case func_max:
            a0 = opt->opreplacements[op.binary.a0];
            a1 = opt->opreplacements[op.binary.a1];
            a0interval = opt->intervals[a0];
            a1interval = opt->intervals[a1];
            return opt_max(op, opt, a0, a1, a0interval, a1interval);
        case func_done:
            a0 = opt->opreplacements[op.unary.a0];
            a0interval = opt->intervals[a0];
            return opt_done(op, opt, a0, a0interval);
        default:
            fprintf(stderr, "Error: unknown operator %d\n", op.f);
            exit(1);
    }
}

void opt_dead_code_elimination(struct optimizer* opt, int last_op) {
    // reuse the opreplacements array to mark the ops that are used
    // mark all ops as unused
    const uint16_t DEAD = 0;
    const uint16_t USED = 1;
    for (int i = 0; i < last_op; i++) {
        opt->opreplacements[i] = DEAD;
    }
    // mark the last op as used
    opt->opreplacements[last_op] = USED;
    // mark the ops that are used by going backwards through the ops
    for (int i = last_op; i >= 0; i--) {
        // if the op is used, mark the arguments as used
        if (opt->opreplacements[i] == USED) {
            struct op op = opt->resultops[i];
            switch (op.f) {
                case func_varx:
                case func_vary:
                case func_varz:
                case func_const:
                    break;
                case func_abs:
                case func_sqrt:
                case func_square:
                case func_neg:
                case func_done:
                    opt->opreplacements[op.unary.a0] = USED;
                    break;
                case func_add:
                case func_sub:
                case func_mul:
                case func_min:
                case func_max:
                    opt->opreplacements[op.binary.a0] = USED;
                    opt->opreplacements[op.binary.a1] = USED;
                    break;
            }
        }
    }
    // now we can remove the unused ops
    // go through the ops and remove the unused ones, by modifying opt->resultops in place
    // we now reuse the opreplacements array to save the new positions of already moved (and thus surviving) ops
    opt->count = 0;
    for (int i = 0; i <= last_op; i++) {
        // if the op is not used, skip it
        if (opt->opreplacements[i] == DEAD) {
            continue;
        }
        // the op is used, so we need to move it to the new position and update its arguments (which were moved)
        // the new position is the current count
        struct op newop;
        newop = opt->resultops[i];
        // update the arguments
        switch (newop.f) {
            case func_varx:
            case func_vary:
            case func_varz:
            case func_const:
                break;
            case func_abs:
            case func_sqrt:
            case func_square:
            case func_neg:
            case func_done:
                newop.unary.a0 = opt->opreplacements[newop.unary.a0];
                break;
            case func_add:
            case func_sub:
            case func_mul:
            case func_min:
            case func_max:
                newop.binary.a0 = opt->opreplacements[newop.binary.a0];
                newop.binary.a1 = opt->opreplacements[newop.binary.a1];
                break;
        }
        // now we can move the op to the new position
        opt->resultops[opt->count] = newop;
        // update the intervals
        opt->intervals[opt->count] = opt->intervals[i];
        // update the opreplacements array
        opt->opreplacements[i] = opt->count;
        opt->count++;
    }
}

void print_ops(struct op ops[]);

struct op* optimize(struct op* ops, float minx, float maxx, float miny, float maxy) {
    // create the optimizer
    struct optimizer* opt = create_optimizer(ops);
    opt->minx = minx;
    opt->maxx = maxx;
    opt->miny = miny;
    opt->maxy = maxy;
    // optimize the ops
    int i = 0;
    for (i = 0; i < 65536; i++) {
        struct op op = ops[i];
        uint16_t newopindex = opt_op(op, opt);
        opt->opreplacements[i] = newopindex;
        if (op.f == func_done) {
            break;
        }
    }
    uint16_t last_op = opt->opreplacements[i];
    //printf("before dce\n");
    //print_ops(opt->resultops);
    opt_dead_code_elimination(opt, last_op);
    //printf("after dce\n");
    //print_ops(opt->resultops);
    //printf("____\n");
    // return the optimized ops
    return opt->resultops;
}

void print_ops(struct op ops[]) {
    int i = 0;
    for (; ops[i].f != func_done; i++) {
        printf("_%x ", i);
        switch (ops[i].f) {
            case func_varx:
                printf("var-x\n");
                break;
            case func_vary:
                printf("var-y\n");
                break;
            case func_varz:
                printf("var-z\n");
                break;
            case func_const:
                printf("const %f\n", ops[i].constant);
                break;
            case func_abs:
                printf("abs _%x\n", ops[i].unary.a0);
                break;
            case func_sqrt:
                printf("sqrt _%x\n", ops[i].unary.a0);
                break;
            case func_square:
                printf("square _%x\n", ops[i].unary.a0);
                break;
            case func_neg:
                printf("neg _%x\n", ops[i].unary.a0);
                break;
            case func_add:
                printf("add _%x _%x\n", ops[i].binary.a0, ops[i].binary.a1);
                break;
            case func_sub:
                printf("sub _%x _%x\n", ops[i].binary.a0, ops[i].binary.a1);
                break;
            case func_mul:
                printf("mul _%x _%x\n", ops[i].binary.a0, ops[i].binary.a1);
                break;
            case func_min:
                printf("min _%x _%x\n", ops[i].binary.a0, ops[i].binary.a1);
                break;
            case func_max:
                printf("max _%x _%x\n", ops[i].binary.a0, ops[i].binary.a1);
                break;
            default:
                printf("unknown\n");
                break;
        }
    }
    printf("_%x done _%x\n", i, ops[i].unary.a0);
}

void render_naive_fragment(struct op ops[], int height, uint8_t* pixels, float minx, float maxx, float miny, float maxy, int startx, int stopx, int starty, int stopy) {
    int width = height; // Assuming square image
    float dx = (maxx - minx) / (width - 1);
    for (int row_index = starty; row_index < stopy; row_index++) {
        float y = miny + (maxy - miny) * row_index / (height - 1);
        float x = minx + dx * startx;
        int index = row_index * width + startx;
        for (int column_index = startx; column_index < stopx; column_index++) {
            float res = dispatch(ops, 0, x, y);
            pixels[index] = (res <= 0.0) ? 0 : 255;
            index++;
            x += dx;
        }
    }
}

void render_image_octree_rec_optimize(struct op ops[], int height, uint8_t* pixels, int startx, int stopx, int starty, int stopy) {
    // proof of concept
    // use intervals to check for uniform color
    //print("==" * level, startx, stopx, starty, stopy)
    float minx = -1, maxx = 1, miny = -1, maxy = 1;
    float a = minx + (maxx - minx) * startx / (height - 1);
    float b = minx + (maxx - minx) * (stopx - 1) / (height - 1);
    float c = miny + (maxy - miny) * starty / (height - 1);
    float d = miny + (maxy - miny) * (stopy - 1) / (height - 1);
    struct op* newprogram = optimize(ops, a, b, c, d);
    // check whether area is small enough to switch to naive evaluation
    if (stopx - startx <= 8 || stopy - starty <= 8) {
        // call naive evaluation
        render_naive_fragment(newprogram, height, pixels, a, b, c, d, startx, stopx, starty, stopy);
        free(newprogram);
        return;
    }
    float midx = (startx + stopx) / 2;
    float midy = (starty + stopy) / 2;
    render_image_octree_rec_optimize(newprogram, height, pixels, startx, midx, starty, midy);
    render_image_octree_rec_optimize(newprogram, height, pixels, midx, stopx, starty, midy);
    render_image_octree_rec_optimize(newprogram, height, pixels, startx, midx, midy, stopy);
    render_image_octree_rec_optimize(newprogram, height, pixels, midx, stopx, midy, stopy);
    free(newprogram);
}

// parsing

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
    //op.destination = count;
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
    //done.destination = count;
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
    render_image_octree_rec_optimize(ops, height, pixels, 0, height, 0, height);
    clock_t end = clock();
    double elapsed = (double)(end - start) / CLOCKS_PER_SEC;
    printf("Elapsed time octree evaluation: %f seconds\n", elapsed);
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
