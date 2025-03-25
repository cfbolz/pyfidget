from __future__ import print_function
import math
import sys

from rpython.rlib import jit, objectmodel

from pyfidget.operations import OPS
from pyfidget.vm import ProgramBuilder, IntervalFrame

LEAVE_AS_IS = sys.maxint

def optimize(program, a, b, c, d, e, f):
    opt = Optimizer(program)
    opt.optimize(a, b, c, d, e, f)
    resindex = program.num_operations() - 1
    result = opt.opreplacements[resindex]
    resultops = opt.resultops
    minimum = opt.intervalframe.minvalues[resindex]
    maximum = opt.intervalframe.maxvalues[resindex]
    if minimum > 0.0 or maximum <= 0:
        return None, minimum, maximum
    result = work_backwards(resultops, result, opt.minvalues, opt.maxvalues)
    res = dce(resultops, result)
    #if not objectmodel.we_are_translated():
    #    print("length before", program.num_operations(), "len after", res.num_operations())
    #    print(res)
    return res, minimum, maximum

@jit.dont_look_inside
def opt_program(*args):
    return optimize(*args)

def symmetric(func):
    def f(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        res = func(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if res == LEAVE_AS_IS:
            return func(self, arg1, arg0, arg1minimum, arg1maximum, arg0minimum, arg0maximum)
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
    abs_of_square = 0
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
        print('abs_of_square', self.abs_of_square)
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

class Optimizer(object):
    def __init__(self, program):
        self.program = program
        num_operations = program.num_operations()
        self.resultops = ProgramBuilder(num_operations)
        # old index -> new index
        self.opreplacements = [0] * num_operations
        self.minvalues = [0.0] * num_operations
        self.maxvalues = [0.0] * num_operations
        self.index = 0
        #self.seen_consts = {}

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
        index = self.index
        self.minvalues[index] = value
        self.maxvalues[index] = value
        self.index = index + 1
        #self.seen_consts[value] = const
        return const

    def optimize(self, a, b, c, d, e, f):
        program = self.program
        self.intervalframe = IntervalFrame(self.program)
        self.intervalframe.setup(self.program.num_operations())
        self.intervalframe.setxyz(a, b, c, d, e, f)

        for index in range(program.num_operations()):
            stats.total_ops += 1
            self.intervalframe._run_op(index)
            func = program.get_func(index)
            stats.ops[ord(func)] += 1
            newop = self._optimize_op(index)
            minimum = self.intervalframe.minvalues[index]
            maximum = self.intervalframe.maxvalues[index]
            if newop == LEAVE_AS_IS:
                # const-folding
                if minimum == maximum and not math.isnan(minimum) and not math.isinf(minimum):
                    stats.constfold += 1
                    newop = self.newconst(minimum)
            if newop == LEAVE_AS_IS:
                newop = self.cse(index, func)
            if newop == LEAVE_AS_IS:
                arg0, arg1 = program.get_args(index)
                newop = self.newop(func, self.get_replacement(arg0), self.get_replacement(arg1))
            if not objectmodel.we_are_translated():
                print(program.op_to_str(index), "-->\t", self.resultops.op_to_str(newop), "\t", self.intervalframe.minvalues[index], self.intervalframe.maxvalues[index])
            self.opreplacements[index] = newop
            if self.resultops.num_operations() > self.index:
                index = self.index
                self.minvalues[index] = minimum
                self.maxvalues[index] = maximum
                self.index = index + 1
            assert self.resultops.num_operations() == self.index

    def cse(self, op, func):
        return LEAVE_AS_IS
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

    def _optimize_op(self, op):
        program = self.program
        func = program.get_func(op)
        if func == OPS.var_x:
            return LEAVE_AS_IS
        if func == OPS.var_y:
            return LEAVE_AS_IS
        if func == OPS.var_z:
            return LEAVE_AS_IS
        arg0, arg1 = program.get_args(op)
        if func == OPS.const:
            return self.newconst(program.consts[arg0])
        arg0minimum = self.intervalframe.minvalues[arg0]
        arg0maximum = self.intervalframe.maxvalues[arg0]
        arg1minimum = self.intervalframe.minvalues[arg1]
        arg1maximum = self.intervalframe.maxvalues[arg1]
        arg0 = self.get_replacement(arg0)
        arg1 = self.get_replacement(arg1)
        #arg0arg0, arg0arg1 = self.resultops.get_args(arg0)
        #arg1arg0, arg1arg1 = self.resultops.get_args(arg1)
        #if (0 != arg0arg0 == arg1 or 0 != arg0arg1 == arg1):
        #    if self.resultops.get_func(arg0) != OPS.const:
        #        print(self.resultops.op_to_str(arg0))
        #        print(self.resultops.op_to_str(arg1))
        #        import pdb;pdb.set_trace()
        if func == OPS.abs:
            return self.opt_abs(arg0, arg0minimum, arg0maximum)
        if func == OPS.square:
            return self.opt_square(arg0, arg0minimum, arg0maximum)
        if func == OPS.neg:
            return self.opt_neg(arg0, arg0minimum, arg0maximum)
        if func == OPS.add:
            return self.opt_add(arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.sub:
            return self.opt_sub(arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.min:
            return self.opt_min(arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.max:
            return self.opt_max(arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.mul:
            return self.opt_mul(arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        return LEAVE_AS_IS

    def opt_abs(self, arg0, arg0minimum, arg0maximum):
        if arg0minimum >= 0:
            stats.abs_pos += 1
            return arg0
        if arg0maximum < 0:
            stats.abs_neg += 1
            return self.defer1(OPS.neg, arg0, arg0minimum, arg0maximum)
        if self.resultops.get_func(arg0) == OPS.neg:
            stats.abs_of_neg += 1
            return self.newop(OPS.abs, self.getarg(arg0, 0))
        return LEAVE_AS_IS

    def opt_square(self, arg0, arg0minimum, arg0maximum):
        if self.resultops.get_func(arg0) == OPS.neg:
            stats.abs_of_square += 1
            return self.newop(OPS.square, self.getarg(arg0, 0))
        return LEAVE_AS_IS

    def opt_neg(self, arg0, arg0minimum, arg0maximum):
        if self.resultops.get_func(arg0) == OPS.neg:
            stats.neg_neg += 1
            return self.getarg(arg0, 0)
        return LEAVE_AS_IS

    @symmetric
    def opt_add(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum == arg0maximum == 0:
            stats.add0 += 1
            return arg1
        #if arg0 == arg1:
        #    arg = self.newconst(2.0)
        #    return ...
        return LEAVE_AS_IS

    def opt_sub(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0 == arg1:
            stats.sub_self += 1
            return self.newconst(0.0)
        if arg0minimum == arg0maximum == 0:
            stats.zero_sub += 1
            return self.defer1(OPS.neg, arg1, arg1minimum, arg1maximum)
        if arg1minimum == arg1maximum == 0:
            stats.sub_zero += 1
            return arg0
        return LEAVE_AS_IS

    @symmetric
    def opt_min(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0maximum < arg1minimum:
            stats.min_range += 1
            return arg0
        if arg0 == arg1:
            stats.min_self += 1
            return arg0
        return LEAVE_AS_IS

    @symmetric
    def opt_max(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum > arg1maximum:
            stats.max_range += 1
            return arg0
        if arg0 == arg1:
            stats.max_self += 1
            return arg0
        return LEAVE_AS_IS

    @symmetric
    def opt_mul(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0 == arg1:
            stats.mul_self += 1
            return self.defer1(OPS.square, arg0, arg0minimum, arg1maximum)
        if arg0minimum == arg0maximum == 0.0:
            stats.mul0 += 1
            return self.newconst(0.0)
        if arg0minimum == arg0maximum == 1.0:
            stats.mul1 += 1
            return arg1
        if arg0minimum == arg0maximum == -1.0:
            stats.mul_neg1 += 1
            return self.defer1(OPS.neg, arg1, arg1minimum, arg1maximum)
        return LEAVE_AS_IS

    def defer1(self, func, arg0, arg0minimum, arg0maximum):
        res = self.opt_op1(func, arg0, arg0minimum, arg0maximum)
        if res is not LEAVE_AS_IS:
            return res
        return self.newop(func, arg0)

    def opt_op1(self, func, arg0, arg0minimum, arg0maximum):
        if func == OPS.abs:
            return self.opt_abs(arg0, arg0minimum, arg0maximum)
        if func == OPS.neg:
            return self.opt_neg(arg0, arg0minimum, arg0maximum)
        return LEAVE_AS_IS


def dce(ops, final_op):
    def mark_alive(new_positions, arg):
        if new_positions[arg] == -1:
            new_positions[arg] = 0
    new_positions = [-1] * ops.num_operations()
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

    output = ProgramBuilder(alive_ops, alive_consts)
    for op in range(final_op + 1):
        if new_positions[index] >= 0:
            func = ops.get_func(op)
            arg0, arg1 = ops.get_args(op)
            if func == OPS.const:
                newop = output.add_const(ops.consts[arg0])
            else:
                numargs = OPS.num_args(func)
                if numargs == 0:
                    arg0 = arg1 = 0
                elif numargs == 1:
                    arg0 = new_positions[arg0]
                    arg1 = 0
                elif numargs == 2:
                    arg0 = new_positions[arg0]
                    arg1 = new_positions[arg1]
                newop = output.add_op(func, arg0, arg1)
            new_positions[index] = newop
        index += 1
    return output.finish()


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
