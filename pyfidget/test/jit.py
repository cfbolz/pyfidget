from rpython import conftest

class o:
    view = False
    viewloops = True
conftest.option = o

from rpython.rlib.nonconst import NonConstant
from rpython.jit.metainterp.test.test_ajit import LLJitMixin

import pytest

from pyfidget.vm import render_image_naive, nested_list_to_ppm, Frame, Program
from pyfidget.parse import parse

class TestLLtype(LLJitMixin):
    def test_quarter(self):
        with open("quarter.vm") as f:
            code = f.read()
        operations = parse(code)
        program = Program(operations)
        def interp():
            render_image_naive(Frame(NonConstant(program)), 50, 50, -2, 2, -2, 2)
        self.meta_interp(interp, [], listcomp=True, listops=True, backendopt=True)