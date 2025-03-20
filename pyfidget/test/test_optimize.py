from pyfidget.optimize import optimize
from pyfidget.parse import parse
from pyfidget.vm import pretty_format, Program
from pyfidget.data import FloatRange


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
