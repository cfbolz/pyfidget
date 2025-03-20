class Value(object):
    index = -1

class Const(Value):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class Operation(Value):
    def __init__(self, name, func, args):
        self.name = name
        self.func = func
        self.args = args

class Program(object):
    def __init__(self, operations):
        self.operations = operations
        for index, op in enumerate(operations):
            op.index = index

class Frame(object):
    def __init__(self, program):
        self.values = [None] * len(program.operations)
        self.program = program

    def run(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        for op in self.program.operations:
            if isinstance(op, Const):
                self.values[op.index] = x.make_constant(op.value)
            elif isinstance(op, Operation):
                if op.func == 'var-x':
                    self.values[op.index] = x
                elif op.func == 'var-y':
                    self.values[op.index] = y
                elif op.func == 'var-z':
                    self.values[op.index] = z
                else:
                    args = [self.values[arg.index] for arg in op.args]
                    if op.func == 'add':
                        res = args[0].add(args[1])
                    elif op.func == 'sub':
                        res = args[0].sub(args[1])
                    elif op.func == 'mul':
                        res = args[0].mul(args[1])
                    elif op.func == 'max':
                        res = args[0].max(args[1])
                    elif op.func == 'min':
                        res = args[0].min(args[1])
                    elif op.func == 'square':
                        res = args[0].square()
                    elif op.func == 'sqrt':
                        res = args[0].sqrt()
                    elif op.func == 'exp':
                        res = args[0].exp()
                    else:
                        raise ValueError("Invalid operation: %s" % op)
                    self.values[op.index] = res
        return self.values[-1]


def pretty_format(operations):
    result = []
    for op in operations:
        if isinstance(op, Const):
            result.append("%s = %s" % (op.name, op.value))
        elif isinstance(op, Operation):
            args = " ".join(arg.name for arg in op.args)
            result.append("%s = %s%s%s" % (op.name, op.func, " " if args else "", args))
    return "\n".join(result)