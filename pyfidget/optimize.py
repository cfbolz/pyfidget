from pyfidget.vm import Const, Operation, Program, IntervalFrame

LEAVE_AS_IS = Const('dummy', -42.0)

def optimize(program, a, b, c, d, e, f):
    opt = Optimizer(program)
    opt.optimize(a, b, c, d, e, f)
    result = opt.opreplacements[len(program.operations) - 1]
    resultops = opt.resultops
    while resultops[-1] is not result:
        resultops.pop()
    return resultops

def symmetric(func):
    def f(self, name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        res = func(self, name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if res is LEAVE_AS_IS:
            return func(self, name, arg1, arg0, arg1minimum, arg1maximum, arg0minimum, arg0maximum)
        return res
    return f

class Optimizer(object):
    def __init__(self, program):
        self.program = program
        self.resultops = []
        self.values = [None] * len(program.operations)
        self.opreplacements = [None] * len(program.operations)
        self.seen_consts = {}

    def get_replacement(self, op):
        while 1:
            nextop = self.opreplacements[op.index]
            if nextop is not None:
                op = nextop
            else:
                return op

    def newop(self, name, func, args):
        newop = Operation(name, func, args)
        self.resultops.append(newop)
        return newop

    def newconst(self, name, value):
        if value in self.seen_consts:
            return self.seen_consts[value]
        const = Const(name, value)
        self.resultops.append(const)
        self.seen_consts[value] = const
        return const

    def optimize(self, a, b, c, d, e, f):
        self.intervalframe = IntervalFrame(self.program)
        self.intervalframe.setup(len(self.program.operations))
        self.intervalframe.setxyz(a, b, c, d, e, f)

        for op in self.program.operations:
            index = op.index
            assert index >= 0
            self.intervalframe._run_op(op)
            newop = self._optimize_op(op)
            if newop is LEAVE_AS_IS:
                newop = Operation(op.name, op.func, [self.get_replacement(arg) for arg in op.args])
                self.resultops.append(newop)
            if newop is not None:
                self.opreplacements[op.index] = newop
            else:
                assert self.opreplacements[op.index] is not None

    def getarg(self, op, i):
        return self.get_replacement(op.args[i])

    def _optimize_op(self, op):
        if isinstance(op, Const):
            return self.newconst(op.name, op.value)
        elif isinstance(op, Operation):
            if op.func == 'var-x':
                return LEAVE_AS_IS
            if op.func == 'var-y':
                return LEAVE_AS_IS
            if op.func == 'var-z':
                return LEAVE_AS_IS
            if not op.args:
                return LEAVE_AS_IS
            minimum = self.intervalframe.minvalues[op.index]
            maximum = self.intervalframe.maxvalues[op.index]
            arg0 = self.getarg(op, 0)
            arg0minimum = self.intervalframe.minvalues[op.args[0].index]
            arg0maximum = self.intervalframe.maxvalues[op.args[0].index]
            if len(op.args) == 1:
                return self.opt_op1(op.func, op.name, arg0, arg0minimum, arg0maximum)
            assert len(op.args) == 2
            arg1 = self.getarg(op, 1)
            arg1minimum = self.intervalframe.minvalues[op.args[1].index]
            arg1maximum = self.intervalframe.maxvalues[op.args[1].index]
            if op.func == 'add':
                return self.opt_add(op.name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
            if op.func == 'min':
                return self.opt_min(op.name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
            if op.func == 'max':
                return self.opt_max(op.name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
            if op.func == 'mul':
                return self.opt_mul(op.name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
            return LEAVE_AS_IS
        else:
            raise ValueError("Invalid operation: %s" % op)
        values[index] = res
        if isinstance(op, Const):
            newop = op
        else:
            assert isinstance(op, Operation)
            newop = Operation(op.name, op.func, [opreplacements[arg.index] for arg in op.args])
        opreplacements[index] = newop
        resultops.append(newop)
        return resultops

    def opt_op1(self, func, name, arg0, arg0minimum, arg0maximum):
        if func == "abs":
            return self.opt_abs(name, arg0, arg0minimum, arg0maximum)
        if func == "neg":
            return self.opt_neg(name, arg0, arg0minimum, arg0maximum)
        return LEAVE_AS_IS

    def opt_abs(self, name, arg0, arg0minimum, arg0maximum):
        if arg0minimum >= 0:
            return arg0
        if arg0maximum < 0:
            return self.defer1("neg", name, arg0, arg0minimum, arg0maximum)
        return LEAVE_AS_IS

    def opt_neg(self, name, arg0, arg0minimum, arg0maximum):
        if arg0.func == 'neg':
            return self.getarg(arg0, 0)
        return LEAVE_AS_IS

    @symmetric
    def opt_add(self, name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum == arg0maximum == 0:
            return arg1
        return LEAVE_AS_IS

    @symmetric
    def opt_min(self, name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0maximum < arg1minimum:
            return arg0
        return LEAVE_AS_IS

    @symmetric
    def opt_max(self, name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum > arg1maximum:
            return arg0
        return LEAVE_AS_IS

    @symmetric
    def opt_mul(self, name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0 is arg1:
            return self.defer1("square", name, arg0, arg0minimum, arg1maximum)
        if arg0minimum == arg0maximum == 0.0:
            return self.newconst(name, 0.0)
        if arg0minimum == arg0maximum == 1.0:
            return arg1
        if arg0minimum == arg0maximum == -1.0:
            return self.defer1("neg", name, arg1, arg1minimum, arg1maximum)
        return LEAVE_AS_IS

    def defer1(self, func, name, arg0, arg0minimum, arg0maximum):
        res = self.opt_op1(func, name, arg0, arg0minimum, arg0maximum)
        if res is not LEAVE_AS_IS:
            return res
        return self.newop(name, func, [arg0])
