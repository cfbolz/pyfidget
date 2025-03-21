from hypothesis import given, strategies, assume
from pyfidget.vm import IntervalFrame, DirectFrame
import math

regular_floats = strategies.floats(allow_nan=False, allow_infinity=False)

def make_range_and_contained_float(a, b, c):
    a, b, c, = sorted([a, b, c])
    intervalframe = IntervalFrame(None)
    intervalframe.setup(10)
    intervalframe.minvalues[0] = a
    intervalframe.maxvalues[0] = c
    frame = DirectFrame(None)
    frame.setup(10)
    frame.floatvalues[0] = b
    return intervalframe, frame
range_and_contained_float = strategies.builds(make_range_and_contained_float, regular_floats, regular_floats, regular_floats)

def contains(intervalframe, frame, index):
    if math.isnan(intervalframe.minvalues[index]) or math.isnan(intervalframe.maxvalues[index]):
        return True
    return intervalframe.minvalues[index] <= frame.floatvalues[index] <= intervalframe.maxvalues[index]

@given(range_and_contained_float)
def test_square(val):
    intervalframe, frame = val
    intervalframe.square(0, 1)
    frame.square(0, 1)
    assert contains(intervalframe, frame, 1)

@given(range_and_contained_float)
def test_abs(val):
    intervalframe, frame = val
    intervalframe.abs(0, 1)
    frame.abs(0, 1)
    assert contains(intervalframe, frame, 1)

@given(range_and_contained_float)
def test_sqrt(val):
    intervalframe, frame = val
    intervalframe.abs(0, 1)
    frame.abs(0, 1)
    intervalframe.sqrt(1, 2)
    frame.sqrt(1, 2)
    assert contains(intervalframe, frame, 2)

@given(range_and_contained_float)
def test_neg(val):
    intervalframe, frame = val
    intervalframe.neg(0, 1)
    frame.neg(0, 1)
    assert contains(intervalframe, frame, 1)

def make_range_and_contained_float2(a1, b1, c1, a2, b2, c2):
    a1, b1, c1 = sorted([a1, b1, c1])
    a2, b2, c2 = sorted([a2, b2, c2])

    intervalframe = IntervalFrame(None)
    intervalframe.setup(10)
    intervalframe.minvalues[0] = a1
    intervalframe.maxvalues[0] = c1
    intervalframe.minvalues[1] = a2
    intervalframe.maxvalues[1] = c2

    frame = DirectFrame(None)
    frame.setup(10)
    frame.floatvalues[0] = b1
    frame.floatvalues[1] = b2

    return intervalframe, frame

range_and_contained_float2 = strategies.builds(
    make_range_and_contained_float2,
    regular_floats, regular_floats, regular_floats,
    regular_floats, regular_floats, regular_floats
)

@given(range_and_contained_float2)
def test_add(val):
    intervalframe, frame = val
    intervalframe.add(0, 1, 2)
    frame.add(0, 1, 2)
    assert contains(intervalframe, frame, 2)

@given(range_and_contained_float2)
def test_sub(val):
    intervalframe, frame = val
    intervalframe.sub(0, 1, 2)
    frame.sub(0, 1, 2)
    assert contains(intervalframe, frame, 2)

@given(range_and_contained_float2)
def test_mul(val):
    intervalframe, frame = val
    intervalframe.mul(0, 1, 2)
    frame.mul(0, 1, 2)
    assert contains(intervalframe, frame, 2)

@given(range_and_contained_float2)
def test_max(val):
    intervalframe, frame = val
    intervalframe.max(0, 1, 2)
    frame.max(0, 1, 2)
    assert contains(intervalframe, frame, 2)

@given(range_and_contained_float2)
def test_min(val):
    intervalframe, frame = val
    intervalframe.min(0, 1, 2)
    frame.min(0, 1, 2)
    assert contains(intervalframe, frame, 2)

