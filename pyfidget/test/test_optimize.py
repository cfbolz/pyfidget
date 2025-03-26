from __future__ import division, print_function
import math

import pytest
from hypothesis import given, strategies, assume

from pyfidget.optimize import optimize, convert_to_shortcut
from pyfidget.parse import parse
from pyfidget.vm import ProgramBuilder, DirectFrame
from pyfidget.vm import IntervalFrame
from pyfidget.operations import OPS

def check_optimize(program, minx=-1000, maxx=1000, miny=-1000, maxy=1000, minz=-1000, maxz=1000, expected=None):
    if isinstance(program, str):
        program = parse(program)
    if isinstance(minx, str):
        assert expected is None
        expected = minx
        minx = -1000

    newops, minimum, maximum = optimize(program, minx, maxx, miny, maxy, minz, maxz)
    if newops:
        check_well_formed(newops)
    else:
        assert (minimum, maximum) == expected
        return
    formatted = newops.pretty_format()
    formatted = formatted.replace(" return_if_pos", "")
    formatted = formatted.replace(" return_if_neg", "")
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
        if op and program.get_func(op) != OPS.const: # ignore first op, due to 0 meaning 'no arg' sometimes
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
    check_optimize(ops, expected=(0.0, 0.0))

@pytest.mark.xfail
def test_cse_invert():
    ops = """
    x var-x
    y var-y
    a min x y
    b min y x
    out sub a b
    """
    check_optimize(ops, expected=(0.0, 0.0))

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

def test_min_backwards_removal():
    ops = """
# [1, 100]
x var-x
# [-10, 10]
y var-y
# [-10, 10
out min x y
"""
    expected = """
y var-y
"""
    check_optimize(ops, 0.01, 10.0, -10, 10, 0, 100, expected)

def test_max_backwards_removal():
    ops = """
# [1, 100]
x var-x

# [-10, 10]
y var-y

# [-100, 100]
z var-z

# [-10, 10]
out min x y

# [-10, 100]
out2 max z out
"""
    expected = """
y var-y
z var-z
out max z y
"""
    check_optimize(ops, 0.01, 10.0, -10, 10, -100, 100, expected)


def test_min_min_self():
    ops = """
x var-x
y var-y
a min x y
b min x a
"""
    expected = """
x var-x
y var-y
a min x y
"""
    check_optimize(ops, expected)

def test_max_max_self():
    ops = """
x var-x
y var-y
a max x y
b max x a
"""
    expected = """
x var-x
y var-y
a max x y
"""
    check_optimize(ops, expected)
# ____________________________________________________________

def test_min_backwards():
    program = """
a var-x
b var-y
out min a b
"""
    program = parse(program)
    convert_to_shortcut(program, 2)
    assert program.pretty_format() == """\
_0 var-x return_if_neg _0 _0
_1 var-y return_if_neg _0 _0
_2 min return_if_neg _0 _1\
"""

    program = """
a var-x
b var-y
out max a b
"""
    program = parse(program)
    convert_to_shortcut(program, 2)
    assert program.pretty_format() == """\
_0 var-x return_if_pos _0 _0
_1 var-y return_if_pos _0 _0
_2 max return_if_pos _0 _1\
"""

def test_min_backwards_further():
    program = """
a var-x
b var-y
c var-z
out min a b
out2 min out c
"""
    program = parse(program)
    convert_to_shortcut(program, 4)
    assert program.pretty_format() == """\
_0 var-x return_if_neg _0 _0
_1 var-y return_if_neg _0 _0
_2 var-z return_if_neg _0 _0
_3 min return_if_neg _0 _1
_4 min return_if_neg _3 _2\
"""

@pytest.mark.xfail
def test_min_max_interleave_backwards():
    program = """
a var-x
b var-y
c var-z
out max c a
out2 min out b
"""
    program = parse(program)
    convert_to_shortcut(program, 4)
    assert program.pretty_format() == """\
_0 var-x _0 _0
_1 var-y return_if_neg _0 _0
_2 var-z return_if_pos _0 _0
_3 max return_if_pos _2 _0
_4 min return_if_neg _3 _1\
"""

# ____________________________________________________________
# random test case generation

regular_floats = strategies.floats(-10000, 10000, allow_nan=False, allow_infinity=False)

all_operation_generators = []
def opgen(func):
    all_operation_generators.append(func)
    return func

@opgen
def make_op0(data, operations):
    func = data.draw(strategies.sampled_from([OPS.var_x, OPS.var_y, OPS.var_z]))
    return operations.add_op(func)

@opgen
def make_const(data, operations):
    return operations.add_const(data.draw(regular_floats))

@opgen
def make_op1(data, operations):
    arg0 = data.draw(strategies.sampled_from(list(operations)))
    func = data.draw(strategies.sampled_from(['square', 'sqrt', 'neg', 'abs']))
    return operations.add_op(OPS.get(func), arg0)

@opgen
def make_op2(data, operations):
    arg0 = data.draw(strategies.sampled_from(list(operations)))
    arg1 = data.draw(strategies.sampled_from(list(operations)))
    func = data.draw(strategies.sampled_from(['add', 'sub', 'min', 'max', 'mul']))
    return operations.add_op(OPS.get(func), arg0, arg1)

@given(strategies.data())
def test_random(data):
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

    ops = ProgramBuilder(num_ops)
    for i in range(num_ops):
        func = data.draw(strategies.sampled_from(all_operation_generators))
        func(data, ops)
    prev_op = ops.num_operations() - 1
    for i in range(num_final_ops):
        arg0 = data.draw(strategies.sampled_from(list(iter(ops))))
        func = data.draw(strategies.sampled_from(['add', 'sub', 'min', 'max', 'mul']))
        if data.draw(strategies.booleans()):
            args = [arg0, prev_op]
        else:
            args = [prev_op, arg0]
        prev_op = ops.add_op(OPS.get(func), *args)
    program = ops
    frame = DirectFrame(program)
    resultops, minimum, maximum = optimize(program, minx, maxx, miny, maxy, 0.0, 0.0)
    if resultops:
        check_well_formed(resultops)
    try:
        res = frame.run_floats(x, y, 0)
    except Exception as e:
        if resultops:
            opt_frame = DirectFrame(resultops)
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
        if resultops:
            opt_frame = DirectFrame(resultops)
            res2 = opt_frame.run_floats(x, y, 0)
            opt_res = " " if res2 > 0 else "#"
        else:
            res2 = minimum
            if minimum > 0:
                opt_res = " "
            else:
                opt_res = "#"
        if not reg_res == opt_res:
            print(x, y, res, res2, reg_res, opt_res)
            print(ops)
            print("----")
            print(resultops)
            import pdb;pdb.set_trace()
            assert 0

