from pyfidget.vm import Const, Operation, Program

def optimize(program, xbounds, ybounds, zbounds):
    resultops = []
    values = [None] * len(program.operations)
    opreplacements = [None] * len(program.operations)
    for op in program.operations:
        index = op.index
        assert index >= 0
        if isinstance(op, Const):
            res = xbounds.make_constant(op.value)
        elif isinstance(op, Operation):
            if op.func == 'var-x':
                res = xbounds
            elif op.func == 'var-y':
                res = ybounds
            elif op.func == 'var-z':
                res = zbounds
                assert res is not None
            else:
                args0 = None
                args1 = None
                if len(op.args) == 1:
                    args0 = values[op.args[0].index]
                elif len(op.args) == 2:
                    args0 = values[op.args[0].index]
                    args1 = values[op.args[1].index]
                else:
                    raise ValueError("number of arguments not supported")
                if op.func == 'add':
                    res = args0.add(args1)
                    if args0.minimum == args0.maximum == 0.0:
                        opreplacements[index] = op.args[1]
                        values[index] = res
                        continue
                    elif args1.minimum == args1.maximum == 0.0:
                        opreplacements[index] = op.args[0]
                        values[index] = res
                        continue
                elif op.func == 'sub':
                    res = args0.sub(args1)
                elif op.func == 'mul':
                    res = args0.mul(args1)
                elif op.func == 'max':
                    res = args0.max(args1)
                elif op.func == 'min':
                    res = args0.min(args1)
                    if args0.maximum < args1.minimum:
                        opreplacements[index] = op.args[0]
                        values[index] = res
                        continue
                elif op.func == 'square':
                    res = args0.square()
                elif op.func == 'sqrt':
                    res = args0.sqrt()
                elif op.func == 'exp':
                    res = args0.exp()
                elif op.func == 'neg':
                    res = args0.neg()
                elif op.func == 'abs':
                    res = args0.abs()
                    if args0.minimum >= 0:
                        values[index] = res
                        opreplacements[index] = op.args[0]
                        continue
                    elif args0.maximum <= 0:
                        newop = Operation(op.name, "neg", [op.args[0]])
                        values[index] = res
                        opreplacements[index] = newop
                        resultops.append(newop)
                        continue
                else:
                    raise ValueError("Invalid operation: %s" % op)
        else:
            raise ValueError("Invalid operation: %s" % op)
        values[index] = res
        if isinstance(op, Const):
            newop = op
        else:
            assert isinstance(op, Operation)
            newop = Operation(op.name, op.func, [opreplacements[arg.index] for arg in op.args])
        opreplacements[index] = newop
        resultops.append(newop)
    return resultops
