# test to parse tanglecube.vm

from pyfidget.parse import parse
from pyfidget.vm import pretty_format

import pytest

def test_parse():
    with open("tanglecube.vm") as f:
        code = f.read()
    operations = parse(code)
    res = pretty_format(operations)
    assert res == """\
_x var-x
_y var-y
_z var-z
_x2 square _x
_x4 square _x2
_y2 square _y
_y4 square _y2
_z2 square _z
_z4 square _z2
_5 const 5.0
_x2_5 mul _x2 _5
_y2_5 mul _y2 _5
_z2_5 mul _z2 _5
_s0 sub _x4 _x2_5
_s1 add _s0 _y4
_s2 sub _s1 _y2_5
_s3 add _s2 _z4
_s4 sub _s3 _z2_5
_10 const 10.0
_out add _s4 _10"""
