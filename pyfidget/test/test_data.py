from hypothesis import given, strategies, assume
from pyfidget.data import Float, FloatRange

regular_floats = strategies.floats(allow_nan=False, allow_infinity=False)

def make_range_and_contained_float(a, b, c):
    a, b, c, = sorted([a, b, c])
    return FloatRange(a, c), Float(b)
range_and_contained_float = strategies.builds(make_range_and_contained_float, regular_floats, regular_floats, regular_floats)

@given(range_and_contained_float)
def test_square(val):
    rng, contained = val
    res = contained.square()
    res_range = rng.square()
    assert res_range.contains(res.value)

@given(range_and_contained_float)
def test_abs(val):
    rng, contained = val
    res = contained.abs()
    res_range = rng.abs()
    assert res_range.contains(res.value)

@given(range_and_contained_float)
def test_sqrt(val):
    rng, contained = val
    rng = rng.abs()
    contained = contained.abs()
    res = contained.sqrt()
    res_range = rng.sqrt()
    assert res_range.contains(res.value)