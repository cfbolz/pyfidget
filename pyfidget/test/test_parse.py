# test to parse tanglecube.vm

from pyfidget.parse import parse

import pytest

def test_parse():
    with open("tanglecube.vm") as f:
        code = f.read()
    operations = parse(code)
    res = operations.pretty_format()
    assert res == """\
_0 var-x _0 _0
_1 var-y _0 _0
_2 var-z _0 _0
_3 square _0 _0
_4 square _3 _0
_5 square _1 _0
_6 square _5 _0
_7 square _2 _0
_8 square _7 _0
_9 const 5.0
_a mul _3 _9
_b mul _5 _9
_c mul _7 _9
_d sub _4 _a
_e add _d _6
_f sub _e _b
_10 add _f _8
_11 sub _10 _c
_12 const 10.0
_13 add _11 _12"""
