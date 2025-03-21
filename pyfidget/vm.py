from __future__ import division, print_function
import math
from rpython.rlib import jit

def should_unroll_one_iteration(program):
    return True

driver_render = jit.JitDriver(greens=['program'],
                              reds=['index', 'row_index', 'column_index', 'width', 'height',
                                    'frame', 'result',
                                    'maxx', 'minx', 'maxy', 'miny'],
                              is_recursive=True)

driver_octree = jit.JitDriver(
        greens=['program'],
        reds='auto',
        should_unroll_one_iteration=should_unroll_one_iteration,
        is_recursive=True)

driver_render_part = jit.JitDriver(
        greens=['program'],
        reds='auto',
        should_unroll_one_iteration=should_unroll_one_iteration,
        is_recursive=True)


class Value(object):
    _immutable_fields_ = ['index', 'name', 'func']
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
        self.func = 'const'

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
        self.program = program

    @jit.unroll_safe
    def run(self):
        program = self.program
        jit.promote(program)
        self.setup(len(program.operations))
        for op in program.operations:
            if jit.we_are_jitted():
                jit.jit_debug(op.tostr())
            if isinstance(op, Const):
                res = self.make_constant(op.value, op.index)
            elif isinstance(op, Operation):
                if op.func == 'var-x':
                    self.get_x(op.index)
                elif op.func == 'var-y':
                    self.get_y(op.index)
                elif op.func == 'var-z':
                    self.get_z(op.index)
                else:
                    arg0index = op.args[0].index
                    arg1index = arg0index
                    if len(op.args) == 2:
                        arg1index = op.args[1].index
                    elif len(op.args) == 1:
                        pass
                    else:
                        raise ValueError("number of arguments not supported")
                    if op.func == 'add':
                        self.add(arg0index, arg1index, op.index)
                    elif op.func == 'sub':
                        self.sub(arg0index, arg1index, op.index)
                    elif op.func == 'mul':
                        self.mul(arg0index, arg1index, op.index)
                    elif op.func == 'max':
                        self.max(arg0index, arg1index, op.index)
                    elif op.func == 'min':
                        self.min(arg0index, arg1index, op.index)
                    elif op.func == 'square':
                        self.square(arg0index, op.index)
                    elif op.func == 'sqrt':
                        self.sqrt(arg0index, op.index)
                    elif op.func == 'exp':
                        self.exp(arg0index, op.index)
                    elif op.func == 'neg':
                        self.neg(arg0index, op.index)
                    elif op.func == 'abs':
                        self.abs(arg0index, op.index)
                    else:
                        raise ValueError("Invalid operation: %s" % op)
            else:
                raise ValueError("Invalid operation: %s" % op)
            index = op.index
            assert index >= 0


class DirectFrame(Frame):
    def __init__(self, program):
        self.program = program

    def run_floats(self, x, y, z):
        self.setxyz(x, y, z)
        self.run()
        return self.floatvalues[len(self.program.operations) - 1]

    def setup(self, length):
        self.floatvalues = [0.0] * length

    def setxyz(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def get_x(self, resindex):
        self.floatvalues[resindex] = self.x

    def get_y(self, resindex):
        self.floatvalues[resindex] = self.y

    def get_z(self, resindex):
        self.floatvalues[resindex] = self.z

    def make_constant(self, const, resindex):
        self.floatvalues[resindex] = const

    def add(self, arg0index, arg1index, resindex):
        self.floatvalues[resindex] = self.floatvalues[arg0index] + self.floatvalues[arg1index]

    def sub(self, arg0index, arg1index, resindex):
        self.floatvalues[resindex] = self.floatvalues[arg0index] - self.floatvalues[arg1index]

    def mul(self, arg0index, arg1index, resindex):
        self.floatvalues[resindex] = self.floatvalues[arg0index] * self.floatvalues[arg1index]

    def max(self, arg0index, arg1index, resindex):
        self.floatvalues[resindex] = max(self.floatvalues[arg0index], self.floatvalues[arg1index])

    def min(self, arg0index, arg1index, resindex):
        self.floatvalues[resindex] = min(self.floatvalues[arg0index], self.floatvalues[arg1index])

    def square(self, arg0index, resindex):
        self.floatvalues[resindex] = self.floatvalues[arg0index] ** 2

    def sqrt(self, arg0index, resindex):
        self.floatvalues[resindex] = self.floatvalues[arg0index] ** 0.5

    def exp(self, arg0index, resindex):
        self.floatvalues[resindex] = math.exp(self.floatvalues[arg0index])

    def neg(self, arg0index, resindex):
        self.floatvalues[resindex] = -self.floatvalues[arg0index]

    def abs(self, arg0index, resindex):
        self.floatvalues[resindex] = abs(self.floatvalues[arg0index])


class IntervalFrame(Frame):
    def __init__(self, program):
        self.program = program

    def run_intervals(self, minx, maxx, miny, maxy, minz, maxz):
        self.setxyz(minx, maxx, miny, maxy, minz, maxz)
        self.run()
        index = len(self.program.operations) - 1
        return self.minvalues[index], self.maxvalues[index]

    def setup(self, length):
        self.minvalues = [0.0] * length
        self.maxvalues = [0.0] * length

    def setxyz(self, minx, maxx, miny, maxy, minz, maxz):
        self.minx = minx
        self.maxx = maxx
        self.miny = miny
        self.maxy = maxy
        self.minz = minz
        self.maxz = maxz

    def get_x(self, resindex):
        self.minvalues[resindex] = self.minx
        self.maxvalues[resindex] = self.maxx

    def get_y(self, resindex):
        self.minvalues[resindex] = self.miny
        self.maxvalues[resindex] = self.maxy

    def get_z(self, resindex):
        self.minvalues[resindex] = self.minz
        self.maxvalues[resindex] = self.maxz

    def make_constant(self, const, resindex):
        self.minvalues[resindex] = const
        self.maxvalues[resindex] = const

    def add(self, arg0index, arg1index, resindex):
        self.minvalues[resindex] = self.minvalues[arg0index] + self.minvalues[arg1index]
        self.maxvalues[resindex] = self.maxvalues[arg0index] + self.maxvalues[arg1index]

    def sub(self, arg0index, arg1index, resindex):
        self.minvalues[resindex] = self.minvalues[arg0index] - self.maxvalues[arg1index]
        self.maxvalues[resindex] = self.maxvalues[arg0index] - self.minvalues[arg1index]

    def mul(self, arg0index, arg1index, resindex):
        min0, max0 = self.minvalues[arg0index], self.maxvalues[arg0index]
        min1, max1 = self.minvalues[arg1index], self.maxvalues[arg1index]
        self.minvalues[resindex] = min(min0 * min1, min0 * max1, max0 * min1, max0 * max1)
        self.maxvalues[resindex] = max(min0 * min1, min0 * max1, max0 * min1, max0 * max1)

    def max(self, arg0index, arg1index, resindex):
        self.minvalues[resindex] = max(self.minvalues[arg0index], self.minvalues[arg1index])
        self.maxvalues[resindex] = max(self.maxvalues[arg0index], self.maxvalues[arg1index])

    def min(self, arg0index, arg1index, resindex):
        self.minvalues[resindex] = min(self.minvalues[arg0index], self.minvalues[arg1index])
        self.maxvalues[resindex] = min(self.maxvalues[arg0index], self.maxvalues[arg1index])

    def square(self, arg0index, resindex):
        min0, max0 = self.minvalues[arg0index], self.maxvalues[arg0index]
        if min0 >= 0:
            self.minvalues[resindex] = min0 * min0
            self.maxvalues[resindex] = max0 * max0
        elif max0 <= 0:
            self.minvalues[resindex] = max0 * max0
            self.maxvalues[resindex] = min0 * min0
        else:
            self.minvalues[resindex] = 0
            self.maxvalues[resindex] = max(min0 * min0, max0 * max0)

    def sqrt(self, arg0index, resindex):
        min0, max0 = self.minvalues[arg0index], self.maxvalues[arg0index]
        if max0 < 0:
            min_res, max_res = float('nan'), float('nan')
        else:
            min_res, max_res = math.sqrt(max(0, min0)), math.sqrt(max0)
        self.minvalues[resindex], self.maxvalues[resindex] = min_res, max_res

    def abs(self, arg0index, resindex):
        min0, max0 = self.minvalues[arg0index], self.maxvalues[arg0index]
        if max0 < 0:
            min_res, max_res = -max0, -min0
        elif min0 >= 0:
            min_res, max_res = min0, max0
        else:
            min_res, max_res = 0, max(-min0, max0)
        self.minvalues[resindex], self.maxvalues[resindex] = min_res, max_res

    def neg(self, arg0index, resindex):
        self.minvalues[resindex] = -self.maxvalues[arg0index]
        self.maxvalues[resindex] = -self.minvalues[arg0index]


def pretty_format(operations):
    result = []
    for op in operations:
        if isinstance(op, Const):
            result.append("%s const %s" % (op.name, op.value))
        elif isinstance(op, Operation):
            args = " ".join(arg.name for arg in op.args)
            result.append("%s %s%s%s" % (op.name, op.func, " " if args else "", args))
    return "\n".join(result)

def render_image_naive(frame, width, height, minx, maxx, miny, maxy):
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
        x = minx + (maxx - minx) * column_index / (width - 1)
        y = miny + (maxy - miny) * row_index / (height - 1)
        res = frame.run_floats(x, y, 0)
        result[index] = " " if res > 0 else "#" # TODO: use int_choose
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
            driver_render_part.jit_merge_point(program=frame.program)
            jit.promote(frame.program)
            x = minx + (maxx - minx) * column_index / (width - 1)
            y = miny + (maxy - miny) * row_index / (height - 1)
            res = frame.run_floats(x, y, 0)
            index = row_index * width + column_index
            result[index] = " " if res > 0 else "#"

def render_image_octree(frame, width, height, minx, maxx, miny, maxy):
    result = [' '] * (width * height)
    render_image_octree_rec(frame, width, height, minx, maxx, miny, maxy, result, 0, width, 0, height)
    return result

LIMIT = 8

def render_image_octree_rec(frame, width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy, level=0):
    # proof of concept
    from pyfidget.data import FloatRange
    driver_octree.jit_merge_point(program=frame.program)
    jit.promote(frame.program)
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
    row = []
    rows = []
    for cell in data:
        if cell == " ":
            row.append("0")
        else:
            row.append("1")
        if len(row) == width:
            row.append('') # rpython workaround, super weird
            row.pop()
            rows.append(" ".join(row))
            row = []
    rows.append("%d %d" % (width, height))
    rows.append("P1")
    rows.reverse()
    assert not row
    return "\n".join(rows)

def flat_list_to_ppm_binary(data, width, height):
    assert len(data) == width * height
    row = []
    rows = []
    nextbyte = 0
    bits = 0
    rowbits = 0
    for cell in data:
        if cell != " ":
            nextbyte |= 1
        bits += 1
        rowbits += 1
        if bits == 8:
            assert 0 <= nextbyte < 256
            row.append(str(nextbyte))
            nextbyte = 0
            bits = 0
        nextbyte <<= 1
        if rowbits == width:
            if bits:
                nextbyte <<= (8 - bits)
                rows.append(str(nextbyte))
                nextbyte = 0
                bits = 0
            rows.append(" ".join(row))
            row = []
            rowbits = 0
    rows.append("%d %d" % (width, height))
    rows.append("P4")
    rows.reverse()
    assert not row
    return "\n".join(rows)


def write_ppm(data, filename, width, height):
    output = flat_list_to_ppm(data, width, height)
    f = open(filename, "w")
    try:
        f.write(output)
    finally:
        f.close()

