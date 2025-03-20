from pyfidget.vm import render_image_naive, nested_list_to_ppm, Frame, Program
from pyfidget.parse import parse

def main(argv):
    if len(argv) != 3:
        print("Usage: %s <input.vm> <output.ppm>" % argv[0])
        return 1
    with open(argv[1]) as f:
        code = f.read()
    operations = parse(code)
    frame = Frame(Program(operations))
    data = render_image_naive(frame, 1000, 1000, -2, 2, -2, 2)
    nested_list_to_ppm(data, argv[2])
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))