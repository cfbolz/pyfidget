import time
from pyfidget.vm import render_image_naive, render_image_octree, write_ppm, DirectFrame, IntervalFrame, \
        render_image_octree_optimize, render_image_octree_optimize_graphviz
from pyfidget.parse import parse
from pyfidget.optimize import stats

from rpython.rlib import jit
from rpython.rlib.objectmodel import we_are_translated
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
    phase = 0
    if len(argv) > 3:
        length = int(argv[3])
        if len(argv) > 4:
            phase = int(argv[4])
    else:
        length = 1024
    preallocated_frame = DirectFrame.new(operations)
    preallocated_frame.setup(operations.num_operations())
    preallocated_frame.delete()
    t1 = time.time()
    args = -1., 1., -1., 1.
    if we_are_translated():
        args = NonConstant(-1.), NonConstant(1.), NonConstant(-1.), NonConstant(1.)
    data = None
    if phase == 0 or phase == 1:
        frame = DirectFrame.new(operations)
        data = render_image_naive(frame, length // 2, length // 2, *args)
        frame.delete()
        t2 = time.time()
        print("time, naive: %s (scaled)" % ((t2 - t1) * 4))
    if phase == 0 or phase == 2:
        t1 = time.time()
        frame = IntervalFrame(operations)
        data = render_image_octree(frame, length, length, *args)
        t2 = time.time()
        print("time, octree: %s" % (t2 - t1))
    if phase == 0 or phase == 3:
        t1 = time.time()
        data = render_image_octree_optimize(operations, length, length, *args)
        t2 = time.time()
        print("time, octree with optimizer: %s" % (t2 - t1))
    if phase == 4:
        t1 = time.time()
        for i in range(500):
            data = render_image_octree_optimize(operations, length, length, *args)
        t2 = time.time()
        print("time, octree with optimizer, 500 times, average: %s" % ((t2 - t1) / 500.))
        return 0
    if phase == 5:
        frame = IntervalFrame(operations)
        output = render_image_octree_optimize_graphviz(frame, length, length, *args)
        with open(argv[2], 'w') as f:
            f.write('\n'.join(output))
        stats.print_stats()
        return 0

    if data is not None:
        write_ppm(data, argv[2], length, length)
    return 0

if __name__ == "__main__":
    import sys
    try:
        sys.exit(main(sys.argv))
    except Exception:
        import pdb; pdb.xpm()
        raise
