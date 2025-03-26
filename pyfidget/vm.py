from __future__ import division, print_function
import time
import math
from rpython.rlib import jit, objectmodel
from pyfidget.operations import OPS

def should_unroll_one_iteration(program):
    return True

driver_render = jit.JitDriver(greens=['program'],
                              reds=['index', 'row_index', 'column_index', 'width', 'height',
                                    'frame', 'result',
                                    'dx', 'minx', 'dy'],
                              is_recursive=True)

driver_octree = jit.JitDriver(
        greens=['program'],
        reds='auto',
        should_unroll_one_iteration=should_unroll_one_iteration,
        is_recursive=True)

driver_octree_optimize = jit.JitDriver(
        greens=['program'],
        reds='auto',
        should_unroll_one_iteration=should_unroll_one_iteration,
        is_recursive=True)

driver_render_part = jit.JitDriver(
        greens=['program'],
        reds='auto',
        should_unroll_one_iteration=should_unroll_one_iteration,
        is_recursive=True)



class ProgramBuilder(object):
    def __init__(self, sizehint=10, const_sizehint=5):
        self.funcs = ['\xff'] * sizehint
        self.arguments = [0] * (sizehint * 2)
        self.index = 0
        self.consts = [0.0] * const_sizehint
        self.const_index = 0

    def reset(self):
        self.index = self.const_index = 0

    def add_const(self, const, name=None):
        arg = self.const_index
        if arg == len(self.consts):
            self.consts = self.consts + [0.0] * len(self.consts)
        self.consts[arg] = const
        self.const_index = arg + 1
        return self.add_op(OPS.const, arg, name=name)

    def add_op(self, func, arg0=0, arg1=0, name=None):
        assert isinstance(arg0, int)
        assert isinstance(arg1, int)
        res = len(self.funcs)
        res = self.index
        self.index = res + 1
        if res == len(self.funcs):
            self.funcs = self.funcs + ['\xff'] * len(self.funcs)
            self.arguments = self.arguments + [0] * len(self.arguments)
        self.funcs[res] = func
        self.arguments[2 * res + 0] = arg0
        self.arguments[2 * res + 1] = arg1
        return res

    def finish(self):
        res = Program(self.funcs[:self.index], self.arguments[:2*self.index], self.consts[:self.const_index])
        return res

    def get_func(self, index):
        assert index < self.index
        return self.funcs[index]

    def num_operations(self):
        return self.index

    def get_func(self, index):
        assert index < self.index
        return self.funcs[index]
    
    @objectmodel.always_inline
    def get_args(self, index):
        assert index < self.index
        return self.arguments[index*2], self.arguments[index*2 + 1]

    def op_to_str(self, i):
        return self.finish().op_to_str(i)
    
    def __str__(self):
        return self.finish().pretty_format()

    def __iter__(self):
        return iter(range(self.num_operations()))


class Program(object):
    def __init__(self, funcs, arguments, consts):
        self.funcs = funcs
        self.arguments = arguments
        self.consts = consts
    
    def num_operations(self):
        return len(self.funcs)

    def size_storage(self):
        return self.num_operations() # for now
    
    def get_func(self, index):
        return self.funcs[index]
    
    @objectmodel.always_inline
    def get_args(self, index):
        return self.arguments[index*2], self.arguments[index*2 + 1]

    def pretty_format(self):
        result = []
        for i in range(self.num_operations()):
            self._op_to_str(i, result)
        return "\n".join(result)

    def op_to_str(self, i):
        r = []
        self._op_to_str(i, r)
        return r[0]

    def _op_to_str(self, i, result):
        func = OPS.char_to_name(self.get_func(i))
        arg0, arg1 = self.get_args(i)
        if func.startswith("const"):
            result.append("_%x %s %s" % (i, func, self.consts[arg0]))
        else:
            result.append("_%x %s _%x _%x" % (i, func, arg0, arg1))

    def __str__(self):
        return self.pretty_format()

    def __iter__(self):
        return iter(range(self.num_operations()))

class Frame(object):
    @jit.unroll_safe
    def run(self):
        program = self.program
        jit.promote(program)
        num_ops = program.num_operations()
        self.setup(num_ops)
        for op in range(num_ops):
            if jit.we_are_jitted():
                jit.jit_debug(program.op_to_str(op))
            self._run_op(op)
    
    def _run_op(self, op):
        program = self.program
        func = program.get_func(op)
        arg0, arg1 = program.get_args(op)
        if func == OPS.const:
            self.make_constant(program.consts[arg0], op)
        elif func == OPS.var_x:
            self.get_x(op)
        elif func == OPS.var_y:
            self.get_y(op)
        elif func == OPS.var_z:
            self.get_z(op)
        elif func == OPS.add:
            self.add(arg0, arg1, op)
        elif func == OPS.sub:
            self.sub(arg0, arg1, op)
        elif func == OPS.mul:
            self.mul(arg0, arg1, op)
        elif func == OPS.max:
            self.max(arg0, arg1, op)
        elif func == OPS.min:
            self.min(arg0, arg1, op)
        elif func == OPS.square:
            self.square(arg0, op)
        elif func == OPS.sqrt:
            self.sqrt(arg0, op)
        elif func == OPS.exp:
            self.exp(arg0, op)
        elif func == OPS.neg:
            self.neg(arg0, op)
        elif func == OPS.abs:
            self.abs(arg0, op)
        else:
            raise ValueError("Invalid operation: %s" % op)

class DirectFrame(object):
    objectmodel.import_from_mixin(Frame)

    def __init__(self, program):
        self.program = program
        self.floatvalues = None

    def run_floats(self, x, y, z):
        self.setxyz(x, y, z)
        return self.run()

    def setup(self, length):
        if self.floatvalues and len(self.floatvalues) == length and not jit.we_are_jitted():
            return
        self.floatvalues = [0.0] * length

    def setxyz(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def run(self):
        from pyfidget.optimize import stats
        program = self.program
        jit.promote(program)
        num_ops = program.num_operations()
        self.setup(num_ops)
        stats.ops_executed += num_ops
        for op in range(num_ops):
            if jit.we_are_jitted():
                jit.jit_debug(program.op_to_str(op))
            func = program.get_func(op)
            res = self._run_op(op, OPS.mask(func))
            if OPS.should_return_if_neg(func):
                if res <= 0.0:
                    stats.ops_skipped += num_ops - op - 1
                    return res
            if OPS.should_return_if_pos(func):
                if res > 0.0:
                    stats.ops_skipped += num_ops - op - 1
                    return res
        return self.floatvalues[self.program.size_storage() - 1]

    def _run_op(self, op, func):
        program = self.program
        arg0, arg1 = program.get_args(op)
        if func == OPS.const:
            res = self.make_constant(program.consts[arg0], op)
        elif func == OPS.var_x:
            res = self.get_x(op)
        elif func == OPS.var_y:
            res = self.get_y(op)
        elif func == OPS.var_z:
            res = self.get_z(op)
        elif func == OPS.add:
            res = self.add(arg0, arg1, op)
        elif func == OPS.sub:
            res = self.sub(arg0, arg1, op)
        elif func == OPS.mul:
            res = self.mul(arg0, arg1, op)
        elif func == OPS.max:
            res = self.max(arg0, arg1, op)
        elif func == OPS.min:
            res = self.min(arg0, arg1, op)
        elif func == OPS.square:
            res = self.square(arg0, op)
        elif func == OPS.sqrt:
            res = self.sqrt(arg0, op)
        elif func == OPS.exp:
            res = self.exp(arg0, op)
        elif func == OPS.neg:
            res = self.neg(arg0, op)
        elif func == OPS.abs:
            res = self.abs(arg0, op)
        else:
            raise ValueError("Invalid operation: %s" % op)
        self.floatvalues[op] = res
        return res

    def get_x(self, resindex):
        return self.x

    def get_y(self, resindex):
        return self.y

    def get_z(self, resindex):
        return self.z

    def make_constant(self, const, resindex):
        return const

    def add(self, arg0index, arg1index, resindex):
        return self.floatvalues[arg0index] + self.floatvalues[arg1index]

    def sub(self, arg0index, arg1index, resindex):
        return self.floatvalues[arg0index] - self.floatvalues[arg1index]

    def mul(self, arg0index, arg1index, resindex):
        return self.floatvalues[arg0index] * self.floatvalues[arg1index]

    def max(self, arg0index, arg1index, resindex):
        return max(self.floatvalues[arg0index], self.floatvalues[arg1index])

    def min(self, arg0index, arg1index, resindex):
        return min(self.floatvalues[arg0index], self.floatvalues[arg1index])

    def square(self, arg0index, resindex):
        val = self.floatvalues[arg0index]
        return val*val

    def sqrt(self, arg0index, resindex):
        return math.sqrt(self.floatvalues[arg0index])

    def exp(self, arg0index, resindex):
        return math.exp(self.floatvalues[arg0index])

    def neg(self, arg0index, resindex):
        return -self.floatvalues[arg0index]

    def abs(self, arg0index, resindex):
        return abs(self.floatvalues[arg0index])

def float_choose(cond, iftrue, iffalse):
    if not jit.we_are_jitted():
        if cond:
            return iftrue
        return iffalse
    return cond * iftrue + (1 - cond) * iffalse

def min(a, b):
    return float_choose(a <= b, a, b)

def max(a, b):
    return float_choose(a <= b, b, a)

def min4(a, b, c, d):
    return min(min(a, b), min(c, d))

def max4(a, b, c, d):
    return max(max(a, b), max(c, d))


class IntervalFrame(object):
    objectmodel.import_from_mixin(Frame)

    def __init__(self, program):
        self.program = program
        self.minvalues = self.maxvalues = None

    def reset(self, program):
        self.program = program

    def run_intervals(self, minx, maxx, miny, maxy, minz, maxz):
        self.setxyz(minx, maxx, miny, maxy, minz, maxz)
        self.run()
        index = self.program.size_storage() - 1
        return self.minvalues[index], self.maxvalues[index]

    def setup(self, length):
        if self.minvalues and len(self.minvalues) >= length:
            return
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

    def _set(self, resindex, minvalue, maxvalue):
        if math.isinf(minvalue) or math.isinf(maxvalue):
            minvalue = maxvalue = float('nan')
        self.minvalues[resindex] = minvalue
        self.maxvalues[resindex] = maxvalue

    def add(self, arg0index, arg1index, resindex):
        arg0minimum = self.minvalues[arg0index]
        arg0maximum = self.maxvalues[arg0index]
        arg1minimum = self.minvalues[arg1index]
        arg1maximum = self.maxvalues[arg1index]
        minvalue, maxvalue = self._add(arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        self._set(resindex, minvalue, maxvalue)

    def _add(self, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        return arg0minimum + arg1minimum, arg0maximum + arg1maximum

    def sub(self, arg0index, arg1index, resindex):
        arg0minimum = self.minvalues[arg0index]
        arg0maximum = self.maxvalues[arg0index]
        arg1minimum = self.minvalues[arg1index]
        arg1maximum = self.maxvalues[arg1index]
        minvalue, maxvalue = self._sub(arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        self._set(resindex, minvalue, maxvalue)

    def _sub(self, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        return arg0minimum - arg1maximum, arg0maximum - arg1minimum

    def mul(self, arg0index, arg1index, resindex):
        arg0minimum = self.minvalues[arg0index]
        arg0maximum = self.maxvalues[arg0index]
        arg1minimum = self.minvalues[arg1index]
        arg1maximum = self.maxvalues[arg1index]
        minvalue, maxvalue = self._mul(arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        self._set(resindex, minvalue, maxvalue)

    def _mul(self, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        return min4(arg0minimum * arg1minimum, arg0minimum * arg1maximum, arg0maximum * arg1minimum, arg0maximum * arg1maximum), \
               max4(arg0minimum * arg1minimum, arg0minimum * arg1maximum, arg0maximum * arg1minimum, arg0maximum * arg1maximum)

    def max(self, arg0index, arg1index, resindex):
        arg0minimum = self.minvalues[arg0index]
        arg0maximum = self.maxvalues[arg0index]
        arg1minimum = self.minvalues[arg1index]
        arg1maximum = self.maxvalues[arg1index]
        minvalue, maxvalue = self._max(arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        self._set(resindex, minvalue, maxvalue)

    def _max(self, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        return max(arg0minimum, arg1minimum), max(arg0maximum, arg1maximum)

    def min(self, arg0index, arg1index, resindex):
        arg0minimum = self.minvalues[arg0index]
        arg0maximum = self.maxvalues[arg0index]
        arg1minimum = self.minvalues[arg1index]
        arg1maximum = self.maxvalues[arg1index]
        minvalue, maxvalue = self._min(arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        self._set(resindex, minvalue, maxvalue)

    def _min(self, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        return min(arg0minimum, arg1minimum), min(arg0maximum, arg1maximum)

    def square(self, arg0index, resindex):
        min0, max0 = self.minvalues[arg0index], self.maxvalues[arg0index]
        self._set(resindex, *self._square(min0, max0))

    def _square(self, min0, max0):
        if min0 >= 0:
            return min0 * min0, max0 * max0
        elif max0 <= 0:
            return max0 * max0, min0 * min0
        else:
            return 0, max(min0 * min0, max0 * max0)

    def sqrt(self, arg0index, resindex):
        min0, max0 = self.minvalues[arg0index], self.maxvalues[arg0index]
        self._set(resindex, *self._sqrt(min0, max0))

    def _sqrt(self, min0, max0):
        if max0 < 0:
            return float('nan'), float('nan')
        return math.sqrt(max(0, min0)), math.sqrt(max0)

    def abs(self, arg0index, resindex):
        min0, max0 = self.minvalues[arg0index], self.maxvalues[arg0index]
        self._set(resindex, *self._abs(min0, max0))

    def _abs(self, min0, max0):
        if max0 < 0:
            return -max0, -min0
        elif min0 >= 0:
            return min0, max0
        else:
            return 0, max(-min0, max0)

    def neg(self, arg0index, resindex):
        self._set(resindex, *self._neg(self.minvalues[arg0index], self.maxvalues[arg0index]))

    def _neg(self, min0, max0):
        return -max0, -min0

    def exp(self, arg0index, resindex):
        min0, max0 = self.minvalues[arg0index], self.maxvalues[arg0index]
        self._set(resindex, *self._exp(min0, max0))

    def _exp(self, min0, max0):
        return math.exp(min0), math.exp(max0)


def render_image_naive(frame, width, height, minx, maxx, miny, maxy):
    minx = float(minx)
    maxx = float(maxx)
    miny = float(miny)
    maxy = float(maxy)
    num_pixels = width * height
    result = ['\x00'] * num_pixels # 0 is white
    index = 0
    row_index = 0
    column_index = 0
    x = minx
    y = miny
    dx = (maxx - minx) / (width - 1)
    dy = (maxy - miny) / (height - 1)
    while 1:
        driver_render.jit_merge_point(program=frame.program, index=index,
                                      row_index=row_index, column_index=column_index,
                                      width=width, height=height, frame=frame,
                                      minx=minx, dx=dx, dy=dy, result=result)
        res = frame.run_floats(x, y, 0)
        result[index] = chr(res <= 0.0)
        index += 1
        column_index += 1
        x += dx
        if column_index >= width:
            x = minx
            column_index = 0
            row_index += 1
            y += dy
            if row_index >= height:
                break
    return result

def render_image_naive_fragment(frame, width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy):
    num_pixels = width * height
    dx = (maxx - minx) / (width - 1)
    for row_index in range(starty, stopy):
        y = miny + (maxy - miny) * row_index / (height - 1)
        x = minx + dx * startx
        index = row_index * width + startx
        for column_index in range(startx, stopx):
            driver_render_part.jit_merge_point(program=frame.program)
            jit.promote(frame.program)
            res = frame.run_floats(x, y, 0)
            result[index] = chr(res <= 0.0)
            index += 1
            x += dx

def render_image_octree(frame, width, height, minx, maxx, miny, maxy):
    result = ['\x00'] * (width * height)
    render_image_octree_rec(frame, width, height, minx, maxx, miny, maxy, result, 0, width, 0, height)
    return result

LIMIT = 8

def render_image_octree_rec(frame, width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy, level=0):
    # proof of concept
    driver_octree.jit_merge_point(program=frame.program)
    jit.promote(frame.program)
    # use intervals to check for uniform color

    #print("==" * level, startx, stopx, starty, stopy)
    a = minx + (maxx - minx) * startx / (width - 1)
    b = minx + (maxx - minx) * (stopx - 1) / (width - 1)
    c = miny + (maxy - miny) * starty / (height - 1)
    d = miny + (maxy - miny) * (stopy - 1) / (height - 1)
    minimum, maximum = frame.run_intervals(a, b, c, d, 0, 0)
    #print("  " * level, x, y, res)
    if maximum < 0:
        # completely inside
        _fill_black(width, height, result, startx, stopx, starty, stopy)
        return
    elif minimum > 0:
        # completely outside, no need to change color
        return

    # check whether area is small enough to switch to naive evaluation
    if stopx - startx <= LIMIT or stopy - starty <= LIMIT:
        render_image_naive_fragment(DirectFrame(frame.program), width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy)
        return
    midx = (startx + stopx) // 2
    midy = (starty + stopy) // 2
    for new_startx, new_stopx in [(startx, midx), (midx, stopx)]:
        for new_starty, new_stopy in [(starty, midy), (midy, stopy)]:
            render_image_octree_rec(frame, width, height, minx, maxx, miny, maxy, result, new_startx, new_stopx, new_starty, new_stopy, level+1)

def render_image_octree_optimize(program, width, height, minx, maxx, miny, maxy):
    result = ['\x00'] * (width * height)
    render_image_octree_rec_optimize(program, width, height, minx, maxx, miny, maxy, result, 0, width, 0, height)
    return result

def render_image_octree_rec_optimize(program, width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy, level=0):
    # proof of concept
    from pyfidget.optimize import opt_program
    # use intervals to check for uniform color

    #print("==" * level, startx, stopx, starty, stopy)
    a = minx + (maxx - minx) * startx / (width - 1)
    b = minx + (maxx - minx) * (stopx - 1) / (width - 1)
    c = miny + (maxy - miny) * starty / (height - 1)
    d = miny + (maxy - miny) * (stopy - 1) / (height - 1)

    direct = stopx - startx <= LIMIT or stopy - starty <= LIMIT
    newprogram, minimum, maximum = opt_program(program, a, b, c, d, 0.0, 0.0, for_direct=direct)
    if maximum < 0:
        # completely inside
        _fill_black(width, height, result, startx, stopx, starty, stopy)
        return
    elif minimum > 0:
        # completely outside, no need to change color
        return
    assert newprogram is not None

    # check whether area is small enough to switch to naive evaluation
    if direct:
        frame = DirectFrame(newprogram)
        render_image_naive_fragment(frame, width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy)
        return
    if newprogram.num_operations() < 500:
        driver_octree_optimize.jit_merge_point(program=newprogram)
    midx = (startx + stopx) // 2
    midy = (starty + stopy) // 2
    for new_startx, new_stopx in [(startx, midx), (midx, stopx)]:
        for new_starty, new_stopy in [(starty, midy), (midy, stopy)]:
            if not objectmodel.we_are_translated():
                print("====================================", level, new_startx, new_stopx, new_starty, new_stopy)
            render_image_octree_rec_optimize(newprogram, width, height, minx, maxx, miny, maxy, result, new_startx, new_stopx, new_starty, new_stopy, level+1)

def render_image_octree_optimize_graphviz(frame, width, height, minx, maxx, miny, maxy):
    result = ['\x00'] * (width * height)
    output = ['digraph G {']
    render_image_octree_rec_optimize_graphviz(frame, width, height, minx, maxx, miny, maxy, result, 0, width, 0, height, output)
    output.append('}')
    return output

def render_image_octree_rec_optimize_graphviz(frame, width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy, output, level=0):
    from pyfidget.optimize import opt_program
    def node_label(a, b, c, d, prefix='l'):
        return "%s_%s_%s_%s_%s" % (prefix, a, b, c, d)
    tt1 = time.time()
    a = minx + (maxx - minx) * startx / (width - 1)
    b = minx + (maxx - minx) * (stopx - 1) / (width - 1)
    c = miny + (maxy - miny) * starty / (height - 1)
    d = miny + (maxy - miny) * (stopy - 1) / (height - 1)
    before_opt = frame.program.num_operations()
    t1 = time.time()
    direct = stopx - startx <= LIMIT or stopy - starty <= LIMIT
    newprogram, minimum, maximum = opt_program(frame.program, a, b, c, d, 0.0, 0.0, for_direct=direct)
    t2 = time.time()
    label = node_label(startx, stopx, starty, stopy)
    descr = ['%s-%s, %s-%s' % (startx, stopx, starty, stopy),
             'time opt %s' % (t2 - t1)]
    if maximum < 0:
        descr.append('fully inside')
        output.append('%s [label="%s", fillcolor=red, shape=box];' % (label, '\\l'.join(descr), frame.program.num_operations()))
        _fill_black(width, height, result, startx, stopx, starty, stopy)
        return
    elif minimum > 0:
        descr.append('fully outside')
        output.append('%s [label="%s", fillcolor=green, shape=box];' % (label, '\\l'.join(descr)))
        return
    descr.append('size program %s (before opt: %s)' % (frame.program.num_operations(), before_opt))

    # check whether area is small enough to switch to naive evaluation
    if direct:
        frame = DirectFrame(newprogram)
        direct_label = node_label(startx, stopx, starty, stopy, 'd')
        t1 = time.time()
        render_image_naive_fragment(frame, width, height, minx, maxx, miny, maxy, result, startx, stopx, starty, stopy)
        t2 = time.time()
        descr.append('time native: %s' % (t2 - t1))
        output.append('%s [fillcolor=yellow, label="%s", shape=box];' % (
            label, '\\l'.join(descr)))
        return
    frame = IntervalFrame(newprogram)
    midx = (startx + stopx) // 2
    midy = (starty + stopy) // 2
    for new_startx, new_stopx in [(startx, midx), (midx, stopx)]:
        for new_starty, new_stopy in [(starty, midy), (midy, stopy)]:
            sublabel = node_label(new_startx, new_stopx, new_starty, new_stopy)
            output.append("%s -> %s" % (label, sublabel))
            render_image_octree_rec_optimize_graphviz(frame, width, height, minx, maxx, miny, maxy, result, new_startx, new_stopx, new_starty, new_stopy, output, level+1)
    tt2 = time.time()
    descr.append('total time %s' % (tt2 - tt1))
    output.append('%s [label="%s", shape=box];' % (label, '\\l'.join(descr)))

def render_image_naive_optimize_check(frame, width, height, minx, maxx, miny, maxy):
    from pyfidget.optimize import opt_program
    opt_frame = DirectFrame(opt_program(frame.program, minx, maxx, miny, maxy, 0.0, 0.0))
    minx = float(minx)
    maxx = float(maxx)
    miny = float(miny)
    maxy = float(maxy)
    num_pixels = width * height
    index = 0
    row_index = 0
    column_index = 0
    while 1:
        x = minx + (maxx - minx) * column_index / (width - 1)
        y = miny + (maxy - miny) * row_index / (height - 1)
        res = frame.run_floats(x, y, 0)
        reg_res = res > 0
        res = opt_frame.run_floats(x, y, 0)
        opt_res = res > 0
        assert opt_res == reg_res
        index += 1
        column_index += 1
        if column_index >= width:
            column_index = 0
            row_index += 1
            if row_index >= height:
                break
    return result

def _fill_black(width, height, result, startx, stopx, starty, stopy):
    for column_index in range(startx, stopx):
        for row_index in range(starty, stopy):
            index = row_index * width + column_index
            result[index] = '\x01'


def flat_list_to_ppm(data, width, height):
    assert len(data) == width * height
    row = [None] * width
    rows = objectmodel.newlist_hint(height)
    rowindex = 0
    for cell in data:
        if cell == "\x00":
            row[rowindex] = "0"
        else:
            row[rowindex] = "1"
        rowindex += 1
        if rowindex == width:
            rows.append(" ".join(row))
            rowindex = 0
    rows.append("%d %d" % (width, height))
    rows.append("P1")
    rows.reverse()
    assert not rowindex
    return "\n".join(rows)

def flat_list_to_ppm_binary(data, width, height):
    assert len(data) == width * height
    row = []
    rows = []
    nextbyte = 0
    bits = 0
    rowbits = 0
    for cell in data:
        if cell != "\x00":
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

