from pyfidget.operations import OPS
from pyfidget.vm import ProgramBuilder

def parse(code):
    lines = code.split("\n")
    program = ProgramBuilder(len(lines))
    opnames = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # ignore comments
        if line.startswith("#"):
            continue
        parts = line.split(' ')
        if len(parts) == 2:
            name, func = parts
            op = program.add_op(OPS.get(func), name=name)
        elif len(parts) >= 3:
            name = parts[0]
            func = parts[1]
            args = parts[2:]
            if func == 'const':
                op = program.add_const(float(args[0]), name)
            else:
                args = [opnames[arg] for arg in args]
                if len(args) == 1:
                    op = program.add_op(OPS.get(func), args[0], name=name)
                elif len(args) == 2:
                    op = program.add_op(OPS.get(func), args[0], args[1], name)
                else:
                    raise ValueError('too many arguments: %s' % line)
        else:
            raise ValueError("Invalid line: %s" % line)
        opnames[name] = op
    return program.finish()
