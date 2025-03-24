import math
import sys

from rpython.rlib import jit, objectmodel

from pyfidget.operations import OPS
from pyfidget.vm import ProgramBuilder, IntervalFrame

LEAVE_AS_IS = sys.maxint

def optimize(program, a, b, c, d, e, f):
    opt = Optimizer(program)
    opt.optimize(a, b, c, d, e, f)
    result = opt.opreplacements[program.num_operations() - 1]
    resultops = opt.resultops
    res = dce(resultops, result)
    if not objectmodel.we_are_translated():
        print("length before", program.num_operations(), "len after", res.num_operations())
        print(res)
    return res

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


class Optimizer(object):
    def __init__(self, program):
        self.program = program
        self.resultops = ProgramBuilder()
        # old index -> new index
        self.opreplacements = [0] * program.num_operations()
        self.seen_consts = {}

    def get_replacement(self, op):
        return self.opreplacements[op]

    def getarg(self, op, index):
        return self.resultops.get_args(op)[index]

    def newop(self, func, arg0=0, arg1=0):
        return self.resultops.add_op(func, arg0, arg1)

    def newconst(self, value):
        if value in self.seen_consts:
            return self.seen_consts[value]
        const = self.resultops.add_const(value)
        self.seen_consts[value] = const
        return const

    def optimize(self, a, b, c, d, e, f):
        program = self.program
        self.intervalframe = IntervalFrame(self.program)
        self.intervalframe.setup(self.program.num_operations())
        self.intervalframe.setxyz(a, b, c, d, e, f)

        for index in range(program.num_operations()):
            self.intervalframe._run_op(index)
            func = program.get_func(index)
            newop = self._optimize_op(index)
            if newop == LEAVE_AS_IS:
                minimum = self.intervalframe.minvalues[index]
                maximum = self.intervalframe.maxvalues[index]
                # const-folding
                if minimum == maximum and not math.isnan(minimum) and not math.isinf(minimum):
                    newop = self.newconst(minimum)
            if newop == LEAVE_AS_IS:
                newop = self.cse(index, func)
            if newop == LEAVE_AS_IS:
                arg0, arg1 = program.get_args(index)
                newop = self.resultops.add_op(func, self.get_replacement(arg0), self.get_replacement(arg1))
            self.opreplacements[index] = newop

    def cse(self, op, func):
        arg0, arg1 = self.program.get_args(op)
        arg0 = self.get_replacement(arg0)
        arg1 = self.get_replacement(arg1)
        num_resultops = self.resultops.num_operations()
        for index in range(num_resultops - 1, max(-1, num_resultops - WINDOW_SIZE), -1):
            other_func = self.resultops.get_func(index)
            if other_func != func:
                continue
            other_arg0, other_arg1 = self.resultops.get_args(index)
            if other_arg0 == arg0 and other_arg1 == arg1:
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
        if func == OPS.abs:
            return self.opt_abs(arg0, arg0minimum, arg0maximum)
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
            return arg0
        if arg0maximum < 0:
            return self.defer1(OPS.neg, arg0, arg0minimum, arg0maximum)
        if self.resultops.get_func(arg0) == OPS.neg:
            return self.newop(OPS.abs, self.getarg(arg0, 0))
        return LEAVE_AS_IS

    def opt_neg(self, arg0, arg0minimum, arg0maximum):
        if self.resultops.get_func(arg0) == OPS.neg:
            return self.getarg(arg0, 0)
        return LEAVE_AS_IS

    @symmetric
    def opt_add(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum == arg0maximum == 0:
            return arg1
        #if arg0 is arg1:
        #    arg = self.newconst(2.0)
        #    return ...
        return LEAVE_AS_IS

    def opt_sub(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0 is arg1:
            return self.newconst(0.0)
        if arg0minimum == arg0maximum == 0:
            return self.defer1(OPS.neg, arg1, arg1minimum, arg1maximum)
        if arg1minimum == arg1maximum == 0:
            return arg0
        return LEAVE_AS_IS

    @symmetric
    def opt_min(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0maximum < arg1minimum:
            return arg0
        if arg0 is arg1:
            return arg0
        return LEAVE_AS_IS

    @symmetric
    def opt_max(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum > arg1maximum:
            return arg0
        if arg0 is arg1:
            return arg0
        return LEAVE_AS_IS

    @symmetric
    def opt_mul(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0 is arg1:
            return self.defer1(OPS.square, arg0, arg0minimum, arg1maximum)
        if arg0minimum == arg0maximum == 0.0:
            return self.newconst(0.0)
        if arg0minimum == arg0maximum == 1.0:
            return arg1
        if arg0minimum == arg0maximum == -1.0:
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
        for arg in args[:OPS.num_args(func)]:
            if new_positions[arg] == -1:
                new_positions[arg] = 0
    funcs = ['\x00'] * alive_ops
    args = [0] * (alive_ops * 2)
    consts = [0.0] * alive_consts
    index = 0

    output = ProgramBuilder()
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
