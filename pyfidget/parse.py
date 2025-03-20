from pyfidget.vm import Operation, Const

def parse(code):
    operations = []
    opnames = {}
    for line in code.split("\n"):
        line = line.strip()
        if not line:
            continue
        # ignore comments
        if line.startswith("#"):
            continue
        parts = line.split(' ')
        if len(parts) == 2:
            name, func = parts
            args = []
            op = Operation(name, func, args)
        elif len(parts) >= 3:
            name = parts[0]
            func = parts[1]
            args = parts[2:]
            if func == 'const':
                op = Const(name, float(args[0]))
            else:
                args = [opnames[arg] for arg in args]
                op = Operation(name, func, args)
        else:
            raise ValueError("Invalid line: %s" % line)
        opnames[name] = op
        operations.append(op)
    return operations