from rpython import conftest

class o:
    view = False
    viewloops = True
conftest.option = o

from rpython.rlib.nonconst import NonConstant
from rpython.jit.metainterp.test.test_ajit import LLJitMixin

import pytest

from pyfidget.vm import render_image_naive, DirectFrame, IntervalFrame, Program
from pyfidget.vm import render_image_octree
from pyfidget.vm import render_image_octree_optimize
from pyfidget.parse import parse

class TestLLtype(LLJitMixin):
    def test_quarter(self):
        with open("quarter.vm") as f:
            code = f.read()
        operations = parse(code)
        program = Program(operations)
        def interp():
            render_image_naive(DirectFrame(NonConstant(program)), NonConstant(50), NonConstant(50),
                               NonConstant(-2.), NonConstant(2.), NonConstant(-2.), NonConstant(2.))
        self.meta_interp(interp, [], listcomp=True, listops=True, backendopt=True)

    def test_quarter_octree(self):
        with open("quarter.vm") as f:
            code = f.read()
        operations = parse(code)
        program = Program(operations)
        def interp():
            render_image_octree(IntervalFrame(NonConstant(program)), NonConstant(256), NonConstant(256),
                                NonConstant(-2.), NonConstant(2.), NonConstant(-2.), NonConstant(2.))
        self.meta_interp(interp, [], listcomp=True, listops=True, backendopt=True)

    def test_quarter_octree_optimize(self):
        with open("quarter.vm") as f:
            code = f.read()
        operations = parse(code)
        program = Program(operations)
        def interp():
            render_image_octree_optimize(IntervalFrame(NonConstant(program)), NonConstant(256), NonConstant(256),
                                NonConstant(-2.), NonConstant(2.), NonConstant(-2.), NonConstant(2.))
        self.meta_interp(interp, [], listcomp=True, listops=True, backendopt=True)
