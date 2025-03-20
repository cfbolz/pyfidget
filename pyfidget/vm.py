from __future__ import division, print_function
from rpython.rlib import jit

driver_run = jit.JitDriver(greens=['program'], reds=['frame'], virtualizables=['frame'])

class Value(object):
    _immutable_fields_ = ['index', 'name']
    index = -1
    name = None

    @jit.elidable
    def tostr(self):
        return self._tostr()

class Const(Value):
    _immutable_fields_ = ['value']
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def _tostr(self):
        return "%s = const %s" % (self.name, self.value)

class Operation(Value):
    _immutable_fields_ = ['func', 'args[*]']
    def __init__(self, name, func, args):
        self.name = name
        self.func = func
        self.args = args

    def __repr__(self):
        return "Operation(%r, %r, %r)" % (self.name, self.func, self.args)

    def _tostr(self):
        return "%s = %s %s" % (self.name, self.func, " ".join([arg.name for arg in self.args]))

class Program(object):
    _immutable_fields_ = ['operations[*]']
    def __init__(self, operations):
        self.operations = operations
        for index, op in enumerate(operations):
            op.index = index

class Frame(object):
    _virtualizable_ = ['values[*]', 'x', 'y', 'z']
    def __init__(self, program):
        self.values = [None] * len(program.operations)
        self.program = program

    def getvalue(self, index):
        assert index >= 0
        return self.values[index]

    def run(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        driver_run.jit_merge_point(program=self.program, frame=self)
        program = self.program
        jit.promote(program)
        for op in program.operations:
            jit.jit_debug(op.tostr())
            if isinstance(op, Const):
                res = self.x.make_constant(op.value)
            elif isinstance(op, Operation):
                if op.func == 'var-x':
                    res = self.x
                elif op.func == 'var-y':
                    res = self.y
                elif op.func == 'var-z':
                    res = self.z
                else:
                    args = [self.getvalue(arg.index) for arg in op.args]
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
                    elif op.func == 'neg':
                        res = args[0].neg()
                    elif op.func == 'abs':
                        res = args[0].abs()
                    else:
                        raise ValueError("Invalid operation: %s" % op)
            else:
                raise ValueError("Invalid operation: %s" % op)
            index = op.index
            assert index >= 0
            self.values[index] = res
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

def render_image_naive(frame, width, height, minx, maxx, miny, maxy):
    from pyfidget.data import Float
    result = [[" " for _ in range(width)] for _ in range(height)]
    for i in range(width):
        for j in range(height):
            x = Float(minx + (maxx - minx) * i / width)
            y = Float(miny + (maxy - miny) * j / height)
            res = frame.run(x, y, Float(0))
            result[j][i] = " " if res.value > 0 else "#"
    return result

def nested_list_to_ppm(data, filename):
    output = []
    output.append("P3")
    output.append("%d %d" % (len(data[0]), len(data)))
    output.append("255")
    for row in data:
        for cell in row:
            if cell == " ":
                output.append("255 255 255")
            else:
                output.append("0 0 0")
    f = open(filename, "w")
    try:
        f.write("\n".join(output))
    finally:
        f.close()

