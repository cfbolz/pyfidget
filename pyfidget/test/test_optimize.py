from __future__ import division, print_function
from pyfidget.optimize import optimize
from pyfidget.parse import parse
from pyfidget.vm import pretty_format, Program
from pyfidget.data import FloatRange

def check_optimize(ops, minx=-1000, maxx=1000, miny=-1000, maxy=1000, minz=-1000, maxz=1000, expected=None):
    program = Program(ops)
    newops = optimize(program, minx, maxx, miny, maxy, minz, maxz)
    check_well_formed(newops)
    formatted = pretty_format(newops)
    if not formatted.strip() == expected.strip():
        print("EXPECTED:")
        print(expected.strip())
        print()
        print("GOT:")
        print(formatted.strip())
        assert 0

def check_well_formed(ops):
    seen = set()
    for op in ops:
        for arg in op.args:
            assert arg in seen
        seen.add(op)

def test_optimize_abs():
    ops = parse("""
x var-x
out abs x
""")
    check_optimize(ops, 0.0, 100.0, -1000, 1000, -1000, 1000, """\
x var-x""")
    
    check_optimize(ops, -100., -1., -1000, 1000, -1000, 1000, """
x var-x
out neg x""")


def test_optimize_add():
    ops = parse("""
zero const 0.0
x var-x
out add x zero
""")
    check_optimize(ops, 0.0, 100.0, -1000, 1000, -1000, 1000, """\
zero const 0.0
x var-x""")

def test_optimize_min():
    ops = parse("""
x var-x
y var-y
a min x y
b min y x
out mul a b
""")
    check_optimize(ops, 0.0, 100.0, 1000, 2000, -1000, 1000, """\
x var-x
y var-y
out square x""")

def test_optimize_neg_neg():
    ops = parse("""
x var-x
a neg x
b neg a
c neg b
d neg c
out square d
""")
    check_optimize(ops, expected="""\
x var-x
a neg x
c neg x
out square x
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
