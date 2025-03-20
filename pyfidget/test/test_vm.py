from __future__ import division, print_function
from pyfidget.vm import Frame, Program, render_image_naive, flat_list_to_ppm
from pyfidget.data import Float, FloatRange
from pyfidget.parse import parse

def quarter_frame():
    with open("quarter.vm") as f:
        code = f.read()
    operations = parse(code)
    program = Program(operations)
    return Frame(program)

def test_quarter():
    frame = quarter_frame()
    res = frame.run(Float(1), Float(2), Float(0))
    assert res.value == 4.5
    output = []
    width = 50
    for i in range(width):
        for j in range(width):
            x = Float(2*(i / width - 0.5))
            y = Float(2*(j / width - 0.5))
            res = frame.run(x, y, Float(0))
            print(x, y, res)
            output.append(" " if res.value > 0 else "#")
        output.append("|\n")
    res = "".join(output)
    assert res == """\
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                     #####                        |
                  ########                        |
                ##########                        |
               ###########                        |
              ############                        |
             #############                        |
            ##############                        |
           ###############                        |
          ################                        |
          ################                        |
         #################                        |
         #################                        |
         #################                        |
        ##################                        |
        ##################                        |
        ##################                        |
        ##################                        |
        ##################                        |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
                                                  |
"""

def test_interval_quarter():
    frame = quarter_frame()
    res = frame.run(FloatRange(1, 2), FloatRange(2, 3), FloatRange(0, 0))
    assert res.minimum == 4.5
    assert res.maximum == 12.5

    res = frame.run(FloatRange(-2, -1), FloatRange(2, 3), FloatRange(0, 0))
    assert res.minimum == 4.5
    assert res.maximum == 12.5

    res = frame.run(FloatRange(-2, 0), FloatRange(0, 2), FloatRange(0, 0))
    assert res.minimum == 0 # ambiguous
    assert res.maximum == 7.5

def test_render_naively():
    frame = quarter_frame()
    data = render_image_naive(frame, 20, 20, -2, 2, -2, 2)
    ppm = flat_list_to_ppm(data, 20, 20)
    assert ppm == """\
P1
20 20
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 1 1 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 1 1 1 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 1 1 1 1 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 1 1 1 1 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"""