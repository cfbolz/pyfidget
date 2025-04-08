# test to parse tanglecube.vm

from pyfidget.parse import parse

import pytest

def test_parse():
    with open("tanglecube.vm") as f:
        code = f.read()
    operations = parse(code)
    res = operations.pretty_format()
    assert res == """\
_0 var-x
_1 var-y
_2 var-z
_3 square _0
_4 square _3
_5 square _1
_6 square _5
_7 square _2
_8 square _7
_9 const 5.000000
_a mul _3 _9
_b mul _5 _9
_c mul _7 _9
_d sub _4 _a
_e add _d _6
_f sub _e _b
_10 add _f _8
_11 sub _10 _c
_12 const 10.000000
_13 add _11 _12"""
