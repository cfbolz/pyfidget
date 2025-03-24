from __future__ import division, print_function
import math

import pytest
from hypothesis import given, strategies, assume

from pyfidget.optimize import optimize
from pyfidget.parse import parse
from pyfidget.vm import Program, DirectFrame
from pyfidget.vm import IntervalFrame
from pyfidget.operations import OPS

def check_optimize(program, minx=-1000, maxx=1000, miny=-1000, maxy=1000, minz=-1000, maxz=1000, expected=None):
    if isinstance(program, str):
        program = parse(program)
    if isinstance(minx, str):
        assert expected is None
        expected = minx
        minx = -1000

    newops, _, _ = optimize(program, minx, maxx, miny, maxy, minz, maxz)
    check_well_formed(newops)
    formatted = newops.pretty_format()
    if not formatted == parse(expected).pretty_format():
        print("EXPECTED:")
        print(expected.strip())
        print()
        print("GOT:")
        print(formatted.strip())
        assert 0

def check_well_formed(program):
    seen = set()
    for op in program:
        if op: # ignore first op, due to 0 meaning 'no arg' sometimes
            for arg in program.get_args(op):
                assert arg in seen
        seen.add(op)

def test_optimize_abs():
    ops = parse("""
x var-x
out abs x
out2 abs out
five const 5.0
out3 sub out2 five
""")
    check_optimize(ops, 0.0, 100.0, -1000, 1000, -1000, 1000, """\
x var-x
five const 5.0
out3 sub x five""")
    
    check_optimize(ops, -100., -1., -1000, 1000, -1000, 1000, """
x var-x
out neg x
five const 5.0
out3 sub out five""")


def test_optimize_add():
    ops = parse("""
zero const 0.0
x var-x
out add x zero
""")
    check_optimize(ops, """\
x var-x""")

#def test_optimize_add_same():
#    ops = parse("""
#x var-x
#out add x x
#""")
#    check_optimize(ops, 0.0, 100.0, -1000, 1000, -1000, 1000, """\
#x var-x
#c2 const 2.0
#out mul c2""")

def test_optimize_sub():
    ops = parse("""
zero const 0.0
x var-x
out sub x zero
""")
    check_optimize(ops, expected="""\
x var-x""")

    ops = parse("""
zero const 0.0
x var-x
out sub zero x
""")
    check_optimize(ops, expected="""\
x var-x
out neg x""")


def test_optimize_min():
    ops = parse("""
x var-x
y var-y
a min x y
b min y x
out mul a b
five const 5.0
out2 sub out five
""")
    check_optimize(ops, 0.0, 100.0, 1000, 2000, -1000, 1000, """\
x var-x
out square x
five const 5.0
out2 sub out five
""")

def test_optimize_max():
    ops = parse("""
x var-x
y var-y
a max x y
b max y x
out mul a b
c const 1000001.0
out2 sub out c
""")
    check_optimize(ops, 0.0, 100.0, 1000, 2000, -1000, 1000, """\
y var-y
out square y
c const 1000001.0
out2 sub out c
""")

def test_optimize_min_max_same():
    ops = parse("""
x var-x
_0 const 0.0
x2 add x _0
a min x x2
b max x x2
out mul a b
c const 10
out2 sub out c
""")
    check_optimize(ops, 0.0, 100.0, 1000, 2000, -1000, 1000, """\
x var-x
out square x
c const 10
out2 sub out c
""")

def test_optimize_neg_neg():
    ops = parse("""
x var-x
a neg x
b neg a
c neg b
d neg c
out square d
c const 10
out2 sub out c
""")
    check_optimize(ops, expected="""\
x var-x
out square x
c const 10
out2 sub out c
""")

def test_optimize_mul():
    ops = parse("""
x var-x
one const 1.0
x_1 mul x one
x_2 mul one x_1
_0 const 0.0
_1 mul x _0
_2 mul _1 x
out add _2 x_2
""")
    check_optimize(ops, expected="""\
x var-x
""")

def test_optimize_mul_to_neg():
    ops = parse("""
x var-x
mone const -1.0
x_1 mul x mone
out mul mone x_1
""")
    check_optimize(ops, expected="""\
x var-x
""")

def test_constfold():
    ops = parse("""
x var-x
mtwo const -2.0
two const 2.0
mfour mul mtwo two
out mul mfour x
""")
    check_optimize(ops, expected="""\
x var-x
mfour const -4.0
out mul mfour x
""")

@pytest.mark.xfail
def test_cse():
    ops = """
    x var-x
    y var-y
    a min x y
    b min x y
    out sub a b
    """
    expected = """
    out const 0.0
    """
    check_optimize(ops, expected)

@pytest.mark.xfail
def test_cse_bug():
    ops = """
x var-x
y var-y
a min x y
b max x y
out sub a b
    """
    expected = """
x var-x
y var-y
a min x y
b max x y
out sub a b
    """
    check_optimize(ops, expected)


def test_abs_neg():
    ops = """
x var-x
a neg x
b abs a
c const 10
out2 sub b c

"""
    expected = """
x var-x
b abs x
c const 10
out2 sub b c
"""
    check_optimize(ops, expected)

def test_square_neg():
    ops = """
x var-x
a neg x
b square a
c const 10
out2 sub b c

"""
    expected = """
x var-x
b square x
c const 10
out2 sub b c
"""
    check_optimize(ops, expected)

# ____________________________________________________________
# random test case generation

regular_floats = strategies.floats(allow_nan=False, allow_infinity=False)

all_operation_generators = []
def opgen(func):
    all_operation_generators.append(func)
    return func

@opgen
def make_op0(data, operations):
    func = data.draw(strategies.sampled_from([OPS.var_x, OPS.var_y, OPS.var_z]))
    return Operation(None, func, [])

@opgen
def make_const(data, operations):
    return Const(None, data.draw(regular_floats))

@opgen
def make_op1(data, operations):
    arg0 = data.draw(strategies.sampled_from(operations))
    func = data.draw(strategies.sampled_from(['square', 'sqrt', 'neg', 'abs']))
    return Operation(None, OPS.get(func), [arg0])

@opgen
def make_op2(data, operations):
    arg0 = data.draw(strategies.sampled_from(operations))
    arg1 = data.draw(strategies.sampled_from(operations))
    func = data.draw(strategies.sampled_from(['add', 'sub', 'min', 'max', 'mul']))
    return Operation(None, OPS.get(func), [arg0, arg1])

@given(strategies.data())
def Xtest_random(data):
    num_ops = data.draw(strategies.integers(1, 100))
    num_final_ops = data.draw(strategies.integers(3, 10))
    a = data.draw(regular_floats)
    b = data.draw(regular_floats)
    c = data.draw(regular_floats)
    minx, x, maxx = sorted([a, b, c])

    a = data.draw(regular_floats)
    b = data.draw(regular_floats)
    c = data.draw(regular_floats)
    miny, y, maxy = sorted([a, b, c])

    ops = []
    for i in range(num_ops):
        func = data.draw(strategies.sampled_from(all_operation_generators))
        ops.append(func(data, ops))
        ops[-1].name = '_%x' % i
    prev_op = ops[-1]
    for i in range(num_final_ops):
        arg0 = data.draw(strategies.sampled_from(ops))
        func = data.draw(strategies.sampled_from(['add', 'sub', 'min', 'max', 'mul']))
        if data.draw(strategies.booleans()):
            args = [arg0, prev_op]
        else:
            args = [prev_op, arg0]
        prev_op = Operation("_fin%x" % i, OPS.get(func), args)
        ops.append(prev_op)
    program = Program(ops)
    frame = DirectFrame(program)
    resultops, _, _ = optimize(program, minx, maxx, miny, maxy, 0.0, 0.0)
    check_well_formed(resultops)
    opt_frame = DirectFrame(Program(resultops))
    try:
        res = frame.run_floats(x, y, 0)
    except Exception as e:
        try:
            res = opt_frame.run_floats(x, y, 0)
        except Exception as e2:
            assert type(e) is type(e2)
        else:
            pass # optimizer is allowed to remove exceptions
    else:
        if math.isnan(res):
            return
        reg_res = " " if res > 0 else "#"
        res2 = opt_frame.run_floats(x, y, 0)
        opt_res = " " if res2 > 0 else "#"
        if not reg_res == opt_res:
            print(x, y, res, res2, reg_res, opt_res)
            formatted = pretty_format(ops)
            print(formatted)
            print("----")
            formatted = pretty_format(resultops)
            print(formatted)
            assert 0

