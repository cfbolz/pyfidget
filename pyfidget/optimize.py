from __future__ import print_function
import math
import sys

from rpython.rlib import jit, objectmodel

from pyfidget.operations import OPS
from pyfidget.vm import ProgramBuilder, IntervalFrame

def optimize(program, a, b, c, d, e, f):
    opt = Optimizer.new(program)
    opt.optimize(a, b, c, d, e, f)
    resindex = program.num_operations() - 1
    result = opt.opreplacements[resindex]
    resultops = opt.resultops
    minimum = opt.intervalframe.minvalues[result]
    maximum = opt.intervalframe.maxvalues[result]
    if minimum > 0.0 or maximum <= 0:
        opt.delete()
        return None, minimum, maximum
    result = work_backwards(resultops, result, opt.intervalframe.minvalues, opt.intervalframe.maxvalues)
    res = opt.dce(result)
    opt.delete()
    #if not objectmodel.we_are_translated():
    #    print("length before", program.num_operations(), "len after", res.num_operations())
    #    print(res)
    return res, minimum, maximum

@jit.dont_look_inside
def opt_program(*args):
    return optimize(*args)

def symmetric(func):
    name = func.func_name[len('opt_'):]
    underscore_name = "_" + name
    func = objectmodel.always_inline(func)
    def f(self, op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        res = func(self, op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if res < 0:
            res = func(self, op, arg1, arg0, arg1minimum, arg1maximum, arg0minimum, arg0maximum)
        if res < 0:
            minimum, maximum = getattr(self.intervalframe, underscore_name)(arg0minimum, arg0maximum, arg1minimum, arg1maximum)
            return self.opt_default(getattr(OPS, name), minimum, maximum, arg0, arg1)
        return res
    return f

WINDOW_SIZE = 100

class Stats(object):
    total_ops = 0
    dedup_const_worked = 0
    cse_worked = 0
    constfold = 0
    abs_pos = 0
    abs_neg = 0
    abs_of_neg = 0
    neg_neg = 0
    square_of_neg = 0
    add0 = 0
    sub_self = 0
    zero_sub = 0
    sub_zero = 0
    min_range = 0
    min_self = 0
    max_range = 0
    max_self = 0
    mul_self = 0
    mul0 = 0
    mul1 = 0
    mul_neg1 = 0

    ops = [0] * 14

    def print_stats(self):
        print('total_ops', self.total_ops)
        print('dedup_const_worked', self.dedup_const_worked)
        print('cse_worked', self.cse_worked)
        print('constfold', self.constfold)
        print('abs_pos', self.abs_pos)
        print('abs_neg', self.abs_neg)
        print('abs_of_neg', self.abs_of_neg)
        print('neg_neg', self.neg_neg)
        print('square_of_neg', self.square_of_neg)
        print('add0', self.add0)
        print('sub_self', self.sub_self)
        print('zero_sub', self.zero_sub)
        print('sub_zero', self.sub_zero)
        print('min_range', self.min_range)
        print('min_self', self.min_self)
        print('max_range', self.max_range)
        print('max_self', self.max_self)
        print('mul_self', self.mul_self)
        print('mul0', self.mul0)
        print('mu1', self.mul1)
        print('mul_neg1', self.mul_neg1)
        print()

        for index, value in enumerate(self.ops):
            print(OPS.char_to_name(chr(index)), value)


stats = Stats()


class MemManager(object):
    unused_optimizer = None

mem_manager = MemManager()


class Optimizer(object):
    def __init__(self, program):
        self.program = program
        num_operations = program.num_operations()
        self.resultops = ProgramBuilder(num_operations)
        self.intervalframe = IntervalFrame(self.program)
        # old index -> new index
        self.opreplacements = [0] * num_operations
        self.minvalues = [0.0] * num_operations
        self.maxvalues = [0.0] * num_operations
        self.index = 0
        #self.seen_consts = {}
        self.next = None

    def _reset(self, program):
        self.resultops.reset()
        self.intervalframe.reset(program)
        num_operations = program.num_operations()
        self.index = 0
        if len(self.opreplacements) < num_operations:
            self.opreplacements = [0] * num_operations
            self.minvalues = [0.0] * num_operations
            self.maxvalues = [0.0] * num_operations
        self.program = program

    @staticmethod
    def new(program):
        if mem_manager.unused_optimizer is not None:
            res = mem_manager.unused_optimizer
            mem_manager.unused_optimizer = res.next
            res.next = None
            res._reset(program)
            return res
        return Optimizer(program)

    def delete(self):
        self.program = None
        self.next = mem_manager.unused_optimizer
        mem_manager.unused_optimizer = self

    def get_replacement(self, op):
        return self.opreplacements[op]

    def getarg(self, op, index):
        return self.resultops.get_args(op)[index]

    def newop(self, func, arg0=0, arg1=0):
        return self.resultops.add_op(func, arg0, arg1)

    def newconst(self, value):
        #if value in self.seen_consts:
        #    stats.dedup_const_worked += 1
        #    return self.seen_consts[value]
        const = self.resultops.add_const(value)
        self.intervalframe.minvalues[const] = value
        self.intervalframe.maxvalues[const] = value
        #self.seen_consts[value] = const
        return const

    def optimize(self, a, b, c, d, e, f):
        program = self.program
        self.intervalframe.setup(self.program.num_operations())
        self.intervalframe.setxyz(a, b, c, d, e, f)

        for index in range(program.num_operations()):
            stats.total_ops += 1
            func = program.get_func(index)
            stats.ops[ord(func)] += 1
            newop = self._optimize_op(index, func)
            self.opreplacements[index] = newop

    def opt_default(self, func, minimum, maximum, arg0=0, arg1=0):
        if minimum == maximum and not math.isnan(minimum) and not math.isinf(minimum):
            stats.constfold += 1
            newop = self.newconst(minimum)
        else:
            newop = self.newop(func, arg0, arg1)
        self.intervalframe._set(newop, minimum, maximum)
        return newop

    def cse(self, op, func):
        return LEAVE_AS_IS # disabled at the moment, seems not worth it
        arg0, arg1 = self.program.get_args(op)
        arg0 = self.get_replacement(arg0)
        arg1 = self.get_replacement(arg1)
        num_resultops = self.resultops.num_operations()
        num_correct_ops = 0
        for index in range(num_resultops - 1, max(-1, num_resultops - WINDOW_SIZE), -1):
            other_func = self.resultops.get_func(index)
            if other_func != func:
                continue
            num_correct_ops += 1
            other_arg0, other_arg1 = self.resultops.get_args(index)
            if other_arg0 == arg0 and other_arg1 == arg1:
                stats.cse_worked += 1
                return index
        return LEAVE_AS_IS

    def _optimize_op(self, op, func):
        program = self.program
        intervalframe = self.intervalframe
        if func == OPS.var_x:
            minimum = self.intervalframe.minx
            maximum = self.intervalframe.maxx
            return self.opt_default(OPS.var_x, minimum, maximum)
        if func == OPS.var_y:
            minimum = self.intervalframe.miny
            maximum = self.intervalframe.maxy
            return self.opt_default(OPS.var_y, minimum, maximum)
        if func == OPS.var_z:
            minimum = self.intervalframe.minz
            maximum = self.intervalframe.maxz
            return self.opt_default(OPS.var_z, minimum, maximum)
        arg0, arg1 = program.get_args(op)
        if func == OPS.const:
            const = program.consts[arg0]
            return self.newconst(const)
        arg0 = self.get_replacement(arg0)
        arg1 = self.get_replacement(arg1)
        arg0minimum = intervalframe.minvalues[arg0]
        arg0maximum = intervalframe.maxvalues[arg0]
        arg1minimum = intervalframe.minvalues[arg1]
        arg1maximum = intervalframe.maxvalues[arg1]
        #arg0arg0, arg0arg1 = self.resultops.get_args(arg0)
        #arg1arg0, arg1arg1 = self.resultops.get_args(arg1)
        #if (0 != arg0arg0 == arg1 or 0 != arg0arg1 == arg1):
        #    if self.resultops.get_func(arg0) != OPS.const:
        #        print(self.resultops.op_to_str(arg0))
        #        print(self.resultops.op_to_str(arg1))
        if func == OPS.abs:
            return self.opt_abs(op, arg0, arg0minimum, arg0maximum)
        if func == OPS.square:
            return self.opt_square(op, arg0, arg0minimum, arg0maximum)
        if func == OPS.sqrt:
            return self.opt_sqrt(op, arg0, arg0minimum, arg0maximum)
        if func == OPS.neg:
            return self.opt_neg(op, arg0, arg0minimum, arg0maximum)
        if func == OPS.add:
            return self.opt_add(op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.sub:
            return self.opt_sub(op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.min:
            return self.opt_min(op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.max:
            return self.opt_max(op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.mul:
            return self.opt_mul(op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        else:
            assert 0, 'unreachable'

    def opt_abs(self, op, arg0, arg0minimum, arg0maximum):
        if arg0minimum >= 0:
            stats.abs_pos += 1
            return arg0
        if arg0maximum < 0:
            stats.abs_neg += 1
            return self.opt_neg(op, arg0, arg0minimum, arg0maximum)
        if self.resultops.get_func(arg0) == OPS.neg:
            stats.abs_of_neg += 1
            arg0 = self.getarg(arg0, 0)
            minimum, maximum = self.intervalframe.minvalues[arg0], self.intervalframe.maxvalues[arg0]
            return self.opt_abs(op, arg0, minimum, maximum)
        minimum, maximum = self.intervalframe._abs(arg0minimum, arg0maximum)
        return self.opt_default(OPS.abs, minimum, maximum, arg0)

    def opt_square(self, op, arg0, arg0minimum, arg0maximum):
        if self.resultops.get_func(arg0) == OPS.neg:
            stats.square_of_neg += 1
            arg0 = self.getarg(arg0, 0)
            minimum, maximum = self.intervalframe.minvalues[arg0], self.intervalframe.maxvalues[arg0]
            return self.opt_square(op, arg0, minimum, maximum)
        minimum, maximum = self.intervalframe._square(arg0minimum, arg0maximum)
        return self.opt_default(OPS.square, minimum, maximum, arg0)

    def opt_sqrt(self, op, arg0, arg0minimum, arg0maximum):
        minimum, maximum = self.intervalframe._sqrt(arg0minimum, arg0maximum)
        return self.opt_default(OPS.sqrt, minimum, maximum, arg0)

    def opt_neg(self, op, arg0, arg0minimum, arg0maximum):
        if self.resultops.get_func(arg0) == OPS.neg:
            stats.neg_neg += 1
            return self.getarg(arg0, 0)
        minimum, maximum = self.intervalframe._neg(arg0minimum, arg0maximum)
        return self.opt_default(OPS.neg, minimum, maximum, arg0)

    @symmetric
    def opt_add(self, op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum == arg0maximum == 0:
            stats.add0 += 1
            return arg1
        return -1

    def opt_sub(self, op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0 == arg1:
            stats.sub_self += 1
            return self.newconst(0.0)
        if arg0minimum == arg0maximum == 0:
            stats.zero_sub += 1
            return self.opt_neg(op, arg1, arg1minimum, arg1maximum)
        if arg1minimum == arg1maximum == 0:
            stats.sub_zero += 1
            return arg0
        minimum, maximum = self.intervalframe._sub(arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        return self.opt_default(OPS.sub, minimum, maximum, arg0, arg1)

    @symmetric
    def opt_min(self, op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0maximum < arg1minimum:
            stats.min_range += 1
            return arg0
        if arg0 == arg1:
            stats.min_self += 1
            return arg0
        return -1

    @symmetric
    def opt_max(self, op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum > arg1maximum:
            stats.max_range += 1
            return arg0
        if arg0 == arg1:
            stats.max_self += 1
            return arg0
        return -1

    @symmetric
    def opt_mul(self, op, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0 == arg1:
            stats.mul_self += 1
            return self.opt_square(op, arg0, arg0minimum, arg0maximum)
        if arg0minimum == arg0maximum == 0.0:
            stats.mul0 += 1
            return self.newconst(0.0)
        if arg0minimum == arg0maximum == 1.0:
            stats.mul1 += 1
            return arg1
        if arg0minimum == arg0maximum == -1.0:
            stats.mul_neg1 += 1
            return self.opt_neg(op, arg1, arg1minimum, arg1maximum)
        return -1

    def dce(self, final_op):
        ops = self.resultops
        def mark_alive(new_positions, arg):
            if new_positions[arg] == -1:
                new_positions[arg] = 0
        # reuse no longer used opreplacements lists
        new_positions = self.opreplacements
        for i in range(final_op):
            new_positions[i] = -1
        new_positions[final_op] = 0
        alive_ops = 0
        alive_consts = 0
        for index in range(final_op, -1, -1):
            if new_positions[index] < 0:
                continue
            alive_ops += 1
            args = ops.get_args(index)
            func = ops.get_func(index)
            if func == OPS.const:
                alive_consts += 1
                continue
            numargs = OPS.num_args(func)
            if numargs == 0:
                pass
            else:
                arg0, arg1 = ops.get_args(index)
                if numargs == 1:
                    mark_alive(new_positions, arg0)
                else:
                    mark_alive(new_positions, arg0)
                    mark_alive(new_positions, arg1)
        index = 0

        # fiddly, but saves time: move the operations in the ops ProgramBuilder in place
        ops.reset()
        for op in range(final_op + 1):
            if new_positions[index] >= 0:
                func = ops.funcs[op]
                arg0 = ops.arguments[op*2]
                if func == OPS.const:
                    newop = ops.add_const(ops.consts[arg0])
                else:
                    arg1 = ops.arguments[op*2 + 1]
                    numargs = OPS.num_args(func)
                    if numargs == 0:
                        arg0 = arg1 = 0
                    elif numargs == 1:
                        arg0 = new_positions[arg0]
                        arg1 = 0
                    elif numargs == 2:
                        arg0 = new_positions[arg0]
                        arg1 = new_positions[arg1]
                    newop = ops.add_op(func, arg0, arg1)
                new_positions[index] = newop
            index += 1
        return ops.finish()


def work_backwards(resultops, result, minvalues, maxvalues):
    if not objectmodel.we_are_translated():
        for op in resultops:
            print(resultops.op_to_str(op), minvalues[op], maxvalues[op])
    def check_gt(resultops, op, minvalues, maxvalues, check_gt, val=0.0):
        while 1:
            func = resultops.get_func(op)
            if not objectmodel.we_are_translated():
                print("round!", OPS.char_to_name(func), "_%x" % op, minvalues[op], maxvalues[op])
            if func == OPS.max:
                arg0, arg1 = resultops.get_args(op)
                narg0 = check_gt(resultops, arg0, minvalues, maxvalues, check_gt, val)
                if narg0 != arg0:
                    resultops.arguments[op * 2 + 0] = narg0
                narg1 = check_gt(resultops, arg1, minvalues, maxvalues, check_gt, val)
                if narg1 != arg1:
                    resultops.arguments[op * 2 + 1] = narg1
            if func == OPS.min:
                arg0, arg1 = resultops.get_args(op)
                if minvalues[arg0] > val:
                    op = arg1
                    continue
                if minvalues[arg1] > val:
                    op = arg0
                    continue
            break
        return op
    otherop = check_gt(resultops, result, minvalues, maxvalues, check_gt)
    if result != otherop:
        if not objectmodel.we_are_translated():
            print("SHORTENED! by", result - otherop, "to", "_%x" % otherop)
    return otherop
