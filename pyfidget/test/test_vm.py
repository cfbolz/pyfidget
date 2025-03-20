from __future__ import division, print_function
from pyfidget.vm import Frame, Program, Value, Const, Operation
from pyfidget.data import Float
from pyfidget.parse import parse

def test_quarter():
    with open("quarter.vm") as f:
        code = f.read()
    operations = parse(code)
    program = Program(operations)
    frame = Frame(program)
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