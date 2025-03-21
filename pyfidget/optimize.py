from pyfidget.vm import Const, Operation, Program, IntervalFrame

LEAVE_AS_IS = Const('dummy', -42.0)

def optimize(program, a, b, c, d, e, f):
    opt = Optimizer(program)
    opt.optimize(a, b, c, d, e, f)
    return opt.resultops

class Optimizer(object):
    def __init__(self, program):
        self.program = program
        self.resultops = []
        self.values = [None] * len(program.operations)
        self.opreplacements = [None] * len(program.operations)

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
            c = Const(op.name, op.value)
            self.resultops.append(c)
            return c
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
            if op.func == "abs":
                return self.opt_abs(op.name, arg0, arg0minimum, arg0maximum, minimum, maximum)
            if op.func == "neg":
                return self.opt_neg(op.name, arg0, arg0minimum, arg0maximum, minimum, maximum)
            if len(op.args) == 1:
                return LEAVE_AS_IS
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
            if op.func == 'sub':
                res = args0.sub(args1)
            elif op.func == 'mul':
                res = args0.mul(args1)
                arg0op = opreplacements[op.args[0].index]
                if arg0op is opreplacements[op.args[1].index]:
                    newop = Operation(op.name, "square", [arg0op])
                    values[index] = res
                    opreplacements[index] = newop
                    resultops.append(newop)
                    return
            elif op.func == 'max':
                res = args0.max(args1)
            elif op.func == 'square':
                res = args0.square()
            elif op.func == 'sqrt':
                res = args0.sqrt()
            elif op.func == 'exp':
                res = args0.exp()
            elif op.func == 'neg':
                res = args0.neg()
                arg0op = opreplacements[op.args[0].index]
                if arg0op.func == 'neg':
                    opreplacements[index] = arg0op.args[0]
                    values[index] = res
                    return
            else:
                raise ValueError("Invalid operation: %s" % op)
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

    def opt_abs(self, name, arg0, arg0minimum, arg0maximum, minimum, maximum):
        if arg0minimum >= 0:
            return arg0
        if arg0maximum < 0:
            return self.newop(name, "neg", [arg0])
        return LEAVE_AS_IS

    def opt_neg(self, name, arg0, arg0minimum, arg0maximum, minimum, maximum):
        if arg0.func == 'neg':
            return self.getarg(arg0, 0)
        return LEAVE_AS_IS

    def opt_add(self, name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum == arg0maximum == 0:
            return arg1
        if arg1minimum == arg1maximum == 0:
            return arg0
        return LEAVE_AS_IS

    def opt_min(self, name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0maximum < arg1minimum:
            return arg0
        if arg0minimum > arg1maximum:
            return arg1
        return LEAVE_AS_IS

    def opt_max(self, name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        return LEAVE_AS_IS

    def opt_mul(self, name, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0 is arg1:
            return self.newop(name, "square", [arg0])
        return LEAVE_AS_IS
