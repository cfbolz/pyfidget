import time
from pyfidget.vm import render_image_naive, write_ppm, Frame, Program
from pyfidget.parse import parse

from rpython.rlib import jit
from rpython.rlib.nonconst import NonConstant

def main(argv):
    # crappy jit argument handling
    for i in range(len(argv)):
        if argv[i] == "--jit":
            if len(argv) == i + 1:
                print("missing argument after --jit")
                return 2
            jitarg = argv[i + 1]
            del argv[i:i+2]
            jit.set_user_param(None, jitarg)
            break

    if len(argv) < 3:
        print("Usage: %s <input.vm> <output.ppm> [length]" % argv[0])
        return 1
    with open(argv[1]) as f:
        code = f.read()
    operations = parse(code)
    frame = Frame(Program(operations))
    t1 = time.time()
    if len(argv) > 3:
        length = int(argv[3])
    else:
        length = 1000
    data = render_image_naive(frame, length, length, NonConstant(-2.), NonConstant(2.), NonConstant(-2.), NonConstant(2.))
    t2 = time.time()
    print("Time: %s" % (t2 - t1))
    write_ppm(data, argv[2], length, length)
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))
