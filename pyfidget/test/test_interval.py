from __future__ import print_function
import pytest
from hypothesis import given, strategies, assume
from pyfidget.vm import IntervalFrame, DirectFrame
import math

regular_floats = strategies.floats(allow_nan=False, allow_infinity=False)

def make_range_and_contained_float(a, b, c):
    a, b, c, = sorted([a, b, c])
    return a, b, c

frame = DirectFrame(None)
intervalframe = IntervalFrame(None)

range_and_contained_float = strategies.builds(make_range_and_contained_float, regular_floats, regular_floats, regular_floats)

def contains(res, rmin, rmax):
    if math.isnan(rmin) or math.isnan(rmax):
        return True
    return rmin <= res <= rmax


@given(range_and_contained_float)
def test_square(val):
    a, b, c = val
    rmin, rmax = intervalframe._square(a, c)
    res = frame.square(b)
    assert contains(res, rmin, rmax)

@given(range_and_contained_float)
def test_abs(val):
    a, b, c = val
    rmin, rmax = intervalframe._abs(a, c)
    res = frame.abs(b)
    assert contains(res, rmin, rmax)

@given(range_and_contained_float)
def test_sqrt(val):
    a, b, c = val
    a = abs(a)
    b = abs(b)
    c = abs(c)
    a, b, c = sorted([a, b, c])
    rmin, rmax = intervalframe._sqrt(a, c)
    res = frame.sqrt(b)
    assert contains(res, rmin, rmax)

@given(range_and_contained_float)
def test_neg(val):
    a, b, c = val
    rmin, rmax = intervalframe._neg(a, c)
    res = frame.neg(b)
    assert contains(res, rmin, rmax)

@given(range_and_contained_float)
def test_exp(val):
    a, b, c = val
    assume(c < 710)  # Prevent overflow
    rmin, rmax = intervalframe._exp(a, c)
    res = frame.exp(b)
    assert contains(res, rmin, rmax)

def make_range_and_contained_float2(a1, b1, c1, a2, b2, c2):
    a1, b1, c1 = sorted([a1, b1, c1])
    a2, b2, c2 = sorted([a2, b2, c2])

    return a1, b1, c1, a2, b2, c2

range_and_contained_float2 = strategies.builds(
    make_range_and_contained_float2,
    regular_floats, regular_floats, regular_floats,
    regular_floats, regular_floats, regular_floats
)

@given(range_and_contained_float2)
def test_add(val):
    a1, b1, c1, a2, b2, c2 = val
    
    rmin, rmax = intervalframe._add(a1, c1, a2, c2)
    res = frame.add(b1, b2)
    assert contains(res, rmin, rmax)

@given(range_and_contained_float2)
def test_sub(val):
    a1, b1, c1, a2, b2, c2 = val
    
    rmin, rmax = intervalframe._sub(a1, c1, a2, c2)
    res = frame.sub(b1, b2)
    assert contains(res, rmin, rmax)

@given(range_and_contained_float2)
def test_mul(val):
    a1, b1, c1, a2, b2, c2 = val
    
    rmin, rmax = intervalframe._mul(a1, c1, a2, c2)
    res = frame.mul(b1, b2)
    assert contains(res, rmin, rmax)

@given(range_and_contained_float2)
def test_max(val):
    a1, b1, c1, a2, b2, c2 = val
    
    rmin, rmax = intervalframe._max(a1, c1, a2, c2)
    res = frame.max(b1, b2)
    assert contains(res, rmin, rmax)

@given(range_and_contained_float2)
def test_min(val):
    a1, b1, c1, a2, b2, c2 = val
    
    rmin, rmax = intervalframe._min(a1, c1, a2, c2)
    res = frame.min(b1, b2)
    assert contains(res, rmin, rmax)
