from __future__ import division, print_function
from rpython.rlib import jit

driver_render = jit.JitDriver(greens=['program'],
                              reds=['index', 'row_index', 'column_index', 'width', 'height',
                                    'frame', 'result',
                                    'maxx', 'minx', 'maxy', 'miny'],
                              is_recursive=True)


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
    #_virtualizable_ = ['values[*]', 'x', 'y', 'z']
    def __init__(self, program):
        self.values = [None] * len(program.operations)
        self.program = program

    def getvalue(self, index):
        assert index >= 0
        return self.values[index]

    @jit.unroll_safe
    def run(self, x, y, z=None):
        self.x = x
        self.y = y
        self.z = z
        program = self.program
        jit.promote(program)
        for op in program.operations:
            if jit.we_are_jitted():
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
                    assert res is not None
                else:
                    args0 = None
                    args1 = None
                    if len(op.args) == 1:
                        args0 = self.getvalue(op.args[0].index)
                    elif len(op.args) == 2:
                        args0 = self.getvalue(op.args[0].index)
                        args1 = self.getvalue(op.args[1].index)
                    else:
                        raise ValueError("number of arguments not supported")
                    if op.func == 'add':
                        res = args0.add(args1)
                    elif op.func == 'sub':
                        res = args0.sub(args1)
                    elif op.func == 'mul':
                        res = args0.mul(args1)
                    elif op.func == 'max':
                        res = args0.max(args1)
                    elif op.func == 'min':
                        res = args0.min(args1)
                    elif op.func == 'square':
                        res = args0.square()
                    elif op.func == 'sqrt':
                        res = args0.sqrt()
                    elif op.func == 'exp':
                        res = args0.exp()
                    elif op.func == 'neg':
                        res = args0.neg()
                    elif op.func == 'abs':
                        res = args0.abs()
                    else:
                        raise ValueError("Invalid operation: %s" % op)
            else:
                raise ValueError("Invalid operation: %s" % op)
            index = op.index
            assert index >= 0
            self.values[index] = res
        res = self.values[len(program.operations) - 1]
        return res


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
    minx = float(minx)
    maxx = float(maxx)
    miny = float(miny)
    maxy = float(maxy)
    result = [[" " for _ in range(width)] for _ in range(height)]
    num_pixels = width * height
    result = [" "] * num_pixels
    index = 0
    row_index = 0
    column_index = 0
    while 1:
        driver_render.jit_merge_point(program=frame.program, index=index,
                                      row_index=row_index, column_index=column_index,
                                      width=width, height=height, frame=frame,
                                      maxx=maxx, minx=minx, maxy=maxy, miny=miny,
                                      result=result)
        x = Float(minx + (maxx - minx) * column_index / width)
        y = Float(miny + (maxy - miny) * row_index / height)
        res = frame.run(x, y, Float(0))
        assert isinstance(res, Float)
        result[index] = " " if res.value > 0 else "#"
        index += 1
        column_index += 1
        if column_index >= width:
            column_index = 0
            row_index += 1
            if row_index >= height:
                break
    return result

def render_image_naive_fragment(frame, width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy):
    from pyfidget.data import Float
    num_pixels = width * height
    for column_index in range(startx, stopx):
        for row_index in range(starty, stopy):
            x = Float(minx + (maxx - minx) * column_index / width)
            y = Float(miny + (maxy - miny) * row_index / height)
            res = frame.run(x, y, x.make_constant(0))
            assert isinstance(res, Float)
            index = row_index * width + column_index
            result[index] = " " if res.value > 0 else "#"

def render_image_octree(frame, width, height, minx, maxx, miny, maxy):
    result = [' '] * (width * height)
    render_image_octree_rec(frame, width, height, minx, maxx, miny, maxy, result, 0, width, 0, height)
    return result

LIMIT = 8

def render_image_octree_rec(frame, width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy, level=0):
    # proof of concept
    from pyfidget.data import FloatRange
    # use intervals to check for uniform color

    #print("==" * level, startx, stopx, starty, stopy)
    x = FloatRange(minx + (maxx - minx) * startx / (width - 1),
                   minx + (maxx - minx) * (stopx - 1) / (width - 1))
    y = FloatRange(miny + (maxy - miny) * starty / (height - 1),
                   miny + (maxy - miny) * (stopy - 1) / (height - 1))
    res = frame.run(x, y, x.make_constant(0))
    #print("  " * level, x, y, res)
    assert isinstance(res, FloatRange)
    if res.maximum < 0:
        # completely inside
        _fill_black(width, height, result, startx, stopx, starty, stopy)
    elif res.minimum > 0:
        # completely outside, no need to change color
        return

    # check whether area is small enough to switch to naive evaluation
    if stopx - startx <= LIMIT or stopy - starty <= LIMIT:
        render_image_naive_fragment(frame, width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy)
        return
    midx = (startx + stopx) // 2
    midy = (starty + stopy) // 2
    for new_startx, new_stopx in [(startx, midx), (midx, stopx)]:
        for new_starty, new_stopy in [(starty, midy), (midy, stopy)]:
            render_image_octree_rec(frame, width, height, minx, maxx, miny, maxy, result, new_startx, new_stopx, new_starty, new_stopy, level+1)


def _fill_black(width, height, result, startx, stopx, starty, stopy):
    for column_index in range(startx, stopx):
        for row_index in range(starty, stopy):
            index = row_index * width + column_index
            result[index] = "#"


def flat_list_to_ppm(data, width, height):
    assert len(data) == width * height
    output = []
    row = []
    output.append("P1")
    output.append("%d %d" % (width, height))
    for cell in data:
        if cell == " ":
            row.append("0")
        else:
            row.append("1")
        if len(row) == width:
            row.append('') # rpython workaround, super weird
            row.pop()
            output.append(" ".join(row))
            row = []
    assert not row
    return "\n".join(output)

def write_ppm(data, filename, width, height):
    output = flat_list_to_ppm(data, width, height)
    f = open(filename, "w")
    try:
        f.write(output)
    finally:
        f.close()

