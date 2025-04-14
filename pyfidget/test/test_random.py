from hypothesis import given, strategies, assume, settings, example

import os

from pyfidget.vm import DirectFrame
from pyfidget.parse import parse
from pyfidget.optimize import opt_program

regular_floats = strategies.floats(-10000, 10000, allow_nan=False, allow_infinity=False)

all_operation_generators = []
def opgen(func):
    all_operation_generators.append(func)
    return func

@opgen
def make_no_op(draw, operations):
    pass # for shrinking

@opgen
def make_op0(draw, operations):
    func = draw(strategies.sampled_from(["var-x", "var-y"]))
    operations.append("_%x %s" % (len(operations), func))

@opgen
def make_const(draw, operations):
    val = draw(regular_floats)
    operations.append("_%x const %f" % (len(operations), val))

@opgen
def make_op1(draw, operations):
    assume(operations)
    arg0 = draw(strategies.integers(0, len(operations) - 1))
    func = draw(strategies.sampled_from(['square', 'sqrt', 'neg', 'abs']))
    operations.append("_%x %s _%x" % (len(operations), func, arg0))

@opgen
def make_op2(draw, operations):
    assume(operations)
    arg0 = draw(strategies.integers(0, len(operations) - 1))
    arg1 = draw(strategies.integers(0, len(operations) - 1))
    func = draw(strategies.sampled_from(['add', 'sub', 'min', 'max', 'mul']))
    operations.append("_%x %s _%x _%x" % (len(operations), func, arg0, arg1))

@strategies.composite
def random_programs(draw):
    num_ops = draw(strategies.integers(1, 100))
    num_final_ops = draw(strategies.integers(0, 10))

    ops = []
    for i in range(num_ops):
        func = draw(strategies.sampled_from(all_operation_generators))
        func(draw, ops)
    assume(ops)
    prev_op = len(ops) - 1
    for i in range(num_final_ops):
        arg0 = draw(strategies.integers(0, len(ops) - 1))
        func = draw(strategies.sampled_from(['add', 'sub', 'min', 'max', 'mul']))
        if draw(strategies.booleans()):
            arg0, arg1 = [arg0, prev_op]
        else:
            arg0, arg1 = [prev_op, arg0]
        prev_op = len(ops)
        ops.append("_%x %s _%x _%x" % (prev_op, func, arg0, arg1))
    return "\n".join(ops)


@settings(deadline=None)
@given(random_programs(), strategies.sampled_from([8, 16, 32, 64, 128, 256, 512, 1024]))
@example('_0 const 512.000001\n_1 square _0\n_2 square _0\n_3 var-x\n_4 var-x\n_5 var-x\n_6 var-x\n_7 var-x\n_8 square _0\n_9 square _0\n_a var-x\n_b square _0\n_c var-x\n_d var-x\n_e var-x\n_f var-x\n_10 square _0\n_11 var-x\n_12 var-x\n_13 var-x\n_14 var-x\n_15 var-x\n_16 var-x\n_17 var-x\n_18 var-x\n_19 var-x\n_1a var-x\n_1b var-x\n_1c square _0\n_1d var-x\n_1e var-x\n_1f var-x\n_20 var-x\n_21 var-x\n_22 var-y\n_23 mul _22 _1\n_24 sub _23 _1\n_25 mul _24 _1\n_26 sub _24 _25', 8)
@example('_0 var-x\n_1 var-x\n_2 square _0\n_3 square _0\n_4 var-x\n_5 square _0\n_6 var-x\n_7 var-x\n_8 square _0\n_9 var-x\n_a var-x\n_b square _0\n_c square _0\n_d var-x\n_e var-x\n_f var-x\n_10 neg _0\n_11 neg _10', 16)
@example('_0 const 0.000000\n_1 var-x\n_2 mul _1 _1\n_3 sqrt _2\n_4 add _3 _0\n_5 add _4 _0\n_6 max _5 _0', 16)
@example('_0 var-x\n_1 add _0 _0\n_2 add _1 _0\n_3 add _2 _0\n_4 add _3 _0\n_5 add _4 _0\n_6 add _5 _0\n_7 add _6 _0\n_8 sub _0 _7\n_9 max _8 _0', 8)
def test_random(program, imagesize):
    frame = DirectFrame(parse(program))
    newprogram, minimum, maximum = opt_program(frame.program, -1, 1, -1, 1, 0.0, 0.0)
    topdir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    executable = os.path.join(topdir, "c-pyfidget-test")
    vmpath = os.path.join(topdir, "random.vm")
    outpath = os.path.join(topdir, "random.ppm")
    with open(vmpath, "w") as f:
        f.write(program)
    
    cmd = "%s %s %s %s" % (executable, vmpath, outpath, imagesize)
    print cmd
    res = os.system(cmd)
    assert not res
    with open(outpath) as f:
        output = f.read()
    #outpath2 = os.path.join(topdir, "random%x.ppm" % hash(output))
    #with open(outpath2, "w") as f:
    #    f.write(output)
    start = "P6\n%s %s\n255\n" % (imagesize, imagesize)
    assert output.startswith(start)
    rest = output[len(start)::3]
    print program
    print "______"
    print newprogram
    print minimum, maximum
    values = [val for x, y, val in value_image_naive(frame, imagesize, imagesize, -1.0, 1.0, -1.0, 1.0)]
    if "error" in values:
        return
    it = value_image_naive(frame, imagesize, imagesize, -1.0, 1.0, -1.0, 1.0)
    for i in range(len(rest)):
        x, y, value = next(it)
        if value == "error":
            continue
        if abs(value) < 1e-5:
            continue # try to work around numerical differences
        char = rest[i]
        char1 = chr(value <= 0.0)
        assert (char1 == '\x00') == (char == '\x00')


def value_image_naive(frame, width, height, minx, maxx, miny, maxy):
    index = 0
    row_index = 0
    column_index = 0
    x = minx
    y = miny
    dx = (maxx - minx) / (width - 1)
    dy = (maxy - miny) / (height - 1)
    while 1:
        try:
            res = frame.run_floats(x, y, 0)
        except ValueError:
            res = "error"
        #print index, x, y, res
        yield x, y, res
        index += 1
        column_index += 1
        x += dx
        if column_index >= width:
            x = minx
            column_index = 0
            row_index += 1
            y = miny + dy * row_index
            if row_index >= height:
                break
