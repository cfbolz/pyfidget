from pyfidget.optimize import optimize
from pyfidget.parse import parse
from pyfidget.vm import pretty_format, Program
from pyfidget.data import FloatRange

def check_optimize(ops, minx=-1000, maxx=1000, miny=-1000, maxy=1000, minz=-1000, maxz=1000, expected=None):
    newops = optimize(Program(ops), FloatRange(0.0, 100.0), FloatRange(-1000, 1000), FloatRange(-1000, 1000))
    check_well_formed(newops)
    assert pretty_format(newops) == expected.strip()

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
    newops = optimize(Program(ops), FloatRange(0.0, 100.0), FloatRange(-1000, 1000), FloatRange(-1000, 1000))
    assert pretty_format(newops) == """\
x var-x"""
    
    newops = optimize(Program(ops), FloatRange(-100., -1.), FloatRange(-1000, 1000), FloatRange(-1000, 1000))
    assert pretty_format(newops) == """\
x var-x
out neg x"""


def test_optimize_add():
    ops = parse("""
zero const 0.0
x var-x
out add x zero
""")
    newops = optimize(Program(ops), FloatRange(0.0, 100.0), FloatRange(-1000, 1000), FloatRange(-1000, 1000))
    assert pretty_format(newops) == """\
zero const 0.0
x var-x"""

def test_optimize_min():
    ops = parse("""
x var-x
y var-y
a min x y
out square a
""")
    newops = optimize(Program(ops), FloatRange(0.0, 100.0), FloatRange(1000, 2000), FloatRange(-1000, 1000))
    assert pretty_format(newops) == """\
x var-x
y var-y
out square x"""

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
