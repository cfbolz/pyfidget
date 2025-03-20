class Value(object):
    pass

class Const(Value):
    def __init__(self, name, value):
        self.name = name
        self.value = value

class Operation(Value):
    def __init__(self, name, func, args):
        self.name = name
        self.func = func
        self.args = args

def pretty_format(operations):
    result = []
    for op in operations:
        if isinstance(op, Const):
            result.append("%s = %s" % (op.name, op.value))
        elif isinstance(op, Operation):
            args = " ".join(arg.name for arg in op.args)
            result.append("%s = %s%s%s" % (op.name, op.func, " " if args else "", args))
    return "\n".join(result)