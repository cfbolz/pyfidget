from __future__ import print_function
import math
import sys

from rpython.rlib import jit, objectmodel
from rpython.tool.udir import udir

from pyfidget.operations import OPS
from pyfidget.vm import ProgramBuilder, IntervalFrame

from dotviewer.graphpage import GraphPage as BaseGraphPage

class GraphPage(BaseGraphPage):
    save_tmp_file = str(udir.join('graph.dot'))

    def compute(self, source, links):
        self.source = source
        self.links = links


def isfinite(val):
    return not math.isinf(val) and not math.isnan(val)

from collections import defaultdict
def collect_uses(p):
    d = defaultdict(list)
    for op in p:
        func = p.get_func(op)
        if func == OPS.const:
            continue
        args = p.get_args(op)
        for arg in args[:OPS.num_args(func)]:
            d[arg].append(op)
    return d

def split_blocks(res, d, allops):
    blocks = defaultdict(list)
    for op in res:
        currop = op
        while 1:
            uses = d[currop]
            if len(uses) != 1 or OPS.mask(res.get_func(currop)) in (OPS.min, OPS.max):
                break
            currop, = uses
        blocks[currop].append(op)
    return blocks


def graph(res, d):
    from dotviewer import graphclient
    out = ['digraph G {']
    allops = set(list(res))
    blocks = split_blocks(res, d, allops)
    minmaxspine = {max(res)}
    for endop in sorted(blocks, reverse=True):
        if OPS.mask(res.get_func(endop)) in (OPS.min, OPS.max):
            if len(d[endop]) == 1 and d[endop][0] in minmaxspine:
                minmaxspine.add(endop)

    edges = set()
    for endop, ops in blocks.items():
        label = []
        for op in ops:
            label.append(res.op_to_str(op))
            args = res.get_args(op)
            func = res.get_func(op)
            if func == OPS.const:
                continue
            for arg in args[:OPS.num_args(func)]:
                if arg not in ops:
                    edges.add((endop, arg))
        label.reverse()
        color = 'yellow' if endop in minmaxspine else 'white'
        out.append("%s [shape=box, label=\"%s\", color=%s];" % (endop, "\\l".join(label), color))
    for endop, arg in edges:
        out.append("%s -> %s;" % (endop, arg))
    out.append("}")
    dot = "\n".join(out)
    with open("out.dot", "w") as f:
        f.write(dot)
    GraphPage(dot, {"_%x" % op: res.op_to_str(op) for op in res}).display()

def optimize(program, a, b, c, d, e, f, for_direct=True):
    for_direct = True
    opt = Optimizer.new(program)
    result = opt.optimize(a, b, c, d, e, f)
    resultops = opt.resultops
    minimum = opt.intervalframe.minvalues[result]
    maximum = opt.intervalframe.maxvalues[result]
    if (isfinite(minimum) and isfinite(maximum)) and (minimum > 0.0 or maximum <= 0):
        opt.delete()
        resultops.delete()
        return None, minimum, maximum
    result = work_backwards(resultops, result, opt.intervalframe.minvalues, opt.intervalframe.maxvalues, for_direct=for_direct)
    res = opt.dce(result)
    #if not objectmodel.we_are_translated() and for_direct:
    #    print(res.pretty_format())
    #    if 50 < res.num_operations() < 1000:
    #        d = collect_uses(res)
    #        #graph(res, d)

    opt.delete()
    #if not objectmodel.we_are_translated():
    #    print("length before", program.num_operations(), "len after", res.num_operations())
    #    print(res)
    return res, minimum, maximum

opt_program = optimize

def symmetric(func):
    name = func.func_name[len('opt_'):]
    underscore_name = "_" + name
    func = objectmodel.always_inline(func)
    def f(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        res = func(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if res < 0:
            res = func(self, arg1, arg0, arg1minimum, arg1maximum, arg0minimum, arg0maximum)
        if res < 0:
            minimum, maximum = getattr(self.intervalframe, underscore_name)(arg0minimum, arg0maximum, arg1minimum, arg1maximum)
            return self.opt_default(getattr(OPS, name), minimum, maximum, arg0, arg1)
        return res
    f.func_name = func.func_name + "_symmetric"
    return f

WINDOW_SIZE = 100

class Stats(object):
    total_ops = 0
    dedup_const_worked = 0
    cse_worked = 0
    constfold = 0
    abs_pos = 0
    abs_neg = 0
    abs_of_neg = 0
    neg_neg = 0
    square_of_neg = 0
    add0 = 0
    sub_self = 0
    zero_sub = 0
    sub_zero = 0
    min_range = 0
    min_self = 0
    min_min_self = 0
    max_range = 0
    max_self = 0
    max_max_self = 0
    mul_self = 0
    mul0 = 0
    mul1 = 0
    mul_neg1 = 0

    backwards_shortening = 0

    ops_executed = 0
    ops_skipped = 0
    ops_optimized = 0
    ops_optimized_checked = 0
    ops_optimized_skipped = 0

    ops = [0] * 14

    def print_stats(self):
        print('total_ops', self.total_ops)
        print('dedup_const_worked', self.dedup_const_worked)
        print('cse_worked', self.cse_worked)
        print('constfold', self.constfold)
        if self.ops[ord(OPS.abs)]:
            print('abs_pos', self.abs_pos)
            print('abs_neg', self.abs_neg)
            print('abs_of_neg', self.abs_of_neg)
        print('neg_neg', self.neg_neg)
        print('square_of_neg', self.square_of_neg)
        print('add0', self.add0)
        print('sub_self', self.sub_self)
        print('zero_sub', self.zero_sub)
        print('sub_zero', self.sub_zero)
        print('min_range', self.min_range)
        print('min_self', self.min_self)
        print('min_min_self', self.min_min_self)
        print('max_range', self.max_range)
        print('max_self', self.max_self)
        print('max_max_self', self.max_max_self)
        print('mul_self', self.mul_self)
        print('mul0', self.mul0)
        print('mu1', self.mul1)
        print('mul_neg1', self.mul_neg1)
        print()
        print('backwards_shortening', self.backwards_shortening)
        print()

        for index, value in enumerate(self.ops):
            print(OPS.char_to_name(chr(index)), value)

        print()
        print('ops_executed', self.ops_executed)
        print('ops_skipped', self.ops_skipped)
        print('ops_optimized', self.ops_optimized)
        print('ops_optimized_checked', self.ops_optimized_checked)
        print('ops_optimized_skipped', self.ops_optimized_skipped)


stats = Stats()


class MemManager(object):
    unused_optimizer = None

mem_manager = MemManager()


class Optimizer(object):
    def __init__(self, program):
        self.program = program
        num_operations = program.num_operations()
        self.resultops = ProgramBuilder.new(num_operations)
        self.intervalframe = IntervalFrame(self.program)
        # old index -> new index
        self.opreplacements = [0] * num_operations
        self.index = 0
        #self.seen_consts = {}
        self.next = None

    def _reset(self, program):
        num_operations = program.num_operations()
        self.resultops = ProgramBuilder.new(num_operations)
        self.intervalframe.reset(program)
        self.index = 0
        if len(self.opreplacements) < num_operations:
            self.opreplacements = [0] * num_operations
        self.program = program

    @staticmethod
    def new(program):
        if mem_manager.unused_optimizer is not None:
            res = mem_manager.unused_optimizer
            mem_manager.unused_optimizer = res.next
            res.next = None
            res._reset(program)
            return res
        return Optimizer(program)

    def delete(self):
        self.program = None
        self.next = mem_manager.unused_optimizer
        mem_manager.unused_optimizer = self

    def get_replacement(self, op):
        return self.opreplacements[op]

    def newop(self, func, arg0=0, arg1=0):
        return self.resultops.add_op(func, arg0, arg1)

    def newconst(self, value):
        #if value in self.seen_consts:
        #    stats.dedup_const_worked += 1
        #    return self.seen_consts[value]
        const = self.resultops.add_const(value)
        self.intervalframe.minvalues[const] = value
        self.intervalframe.maxvalues[const] = value
        #self.seen_consts[value] = const
        return const

    def optimize(self, a, b, c, d, e, f):
        program = self.program
        self.intervalframe.setup(self.program.num_operations())
        self.intervalframe.setxyz(a, b, c, d, e, f)
        numops = program.num_operations()
        stats.ops_optimized += numops
        for index in range(numops):
            stats.total_ops += 1
            func = program.get_func(index)
            newop = self._optimize_op(index)
            if OPS.should_return_if_pos(func):
                stats.ops_optimized_checked += 1
                if self.intervalframe.minvalues[newop] > 0:
                    stats.ops_optimized_skipped += numops - index - 1
                    return newop
            if OPS.should_return_if_neg(func):
                stats.ops_optimized_checked += 1
                if self.intervalframe.maxvalues[newop] <= 0.0:
                    stats.ops_optimized_skipped += numops - index - 1
                    return newop
            self.opreplacements[index] = newop
        return self.opreplacements[numops - 1]

    def get_func(self, index):
        return OPS.mask(self.resultops.get_func(index))

    def opt_default(self, func, minimum, maximum, arg0=0, arg1=0):
        if minimum == maximum and not math.isnan(minimum) and not math.isinf(minimum):
            stats.constfold += 1
            newop = self.newconst(minimum)
        else:
            #newop = self.cse(func, arg0, arg1)
            #if newop < 0:
                newop = self.newop(func, arg0, arg1)
        self.intervalframe._set(newop, minimum, maximum)
        return newop

    def cse(self, func, arg0, arg1):
        num_resultops = self.resultops.num_operations()
        symmetric = OPS.is_symmetric(func)
        for index in range(num_resultops - 1, max(-1, num_resultops - WINDOW_SIZE), -1):
            other_func = self.resultops.get_func(index)
            if other_func != func:
                continue
            other_arg0, other_arg1 = self.resultops.get_args(index)
            if (other_arg0 == arg0 and other_arg1 == arg1) or (
                    symmetric and other_arg1 == arg0 and other_arg0 == arg1):
                stats.cse_worked += 1
                return index
        return -1

    @objectmodel.always_inline
    def _optimize_op(self, op):
        program = self.program
        intervalframe = self.intervalframe
        func, arg0, arg1 = program.get_func_and_args(op)
        assert arg0 >= 0
        assert arg1 >= 0
        func = OPS.mask(func)
        stats.ops[ord(func)] += 1
        if func == OPS.var_x:
            minimum = intervalframe.minx
            maximum = intervalframe.maxx
            return self.opt_default(OPS.var_x, minimum, maximum)
        if func == OPS.var_y:
            minimum = intervalframe.miny
            maximum = intervalframe.maxy
            return self.opt_default(OPS.var_y, minimum, maximum)
        if func == OPS.var_z:
            minimum = intervalframe.minz
            maximum = intervalframe.maxz
            return self.opt_default(OPS.var_z, minimum, maximum)
        if func == OPS.const:
            const = program.consts[arg0]
            return self.newconst(const)
        arg0 = self.get_replacement(arg0)
        arg1 = self.get_replacement(arg1)
        assert arg0 >= 0
        assert arg1 >= 0
        arg0minimum = intervalframe.minvalues[arg0]
        arg0maximum = intervalframe.maxvalues[arg0]
        arg1minimum = intervalframe.minvalues[arg1]
        arg1maximum = intervalframe.maxvalues[arg1]
        #arg0arg0, arg0arg1 = self.resultops.get_args(arg0)
        #arg1arg0, arg1arg1 = self.resultops.get_args(arg1)
        #if (0 != arg0arg0 == arg1 or 0 != arg0arg1 == arg1):
        #    if self.resultops.get_func(arg0) != OPS.const:
        #        print(self.resultops.op_to_str(arg0))
        #        print(self.resultops.op_to_str(arg1))
        if func == OPS.abs:
            return self.opt_abs(arg0, arg0minimum, arg0maximum)
        if func == OPS.square:
            return self.opt_square(arg0, arg0minimum, arg0maximum)
        if func == OPS.sqrt:
            return self.opt_sqrt(arg0, arg0minimum, arg0maximum)
        if func == OPS.neg:
            return self.opt_neg(arg0, arg0minimum, arg0maximum)
        if func == OPS.add:
            return self.opt_add(arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.sub:
            return self.opt_sub(arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.min:
            return self.opt_min(arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.max:
            return self.opt_max(arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        if func == OPS.mul:
            return self.opt_mul(arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        else:
            assert 0, 'unreachable'

    def opt_abs(self, arg0, arg0minimum, arg0maximum):
        if arg0minimum >= 0:
            stats.abs_pos += 1
            return arg0
        if arg0maximum < 0:
            stats.abs_neg += 1
            return self.opt_neg(arg0, arg0minimum, arg0maximum)
        func, arg0arg0, _ = self.resultops.get_func_and_args(arg0)
        if OPS.mask(func) == OPS.neg:
            stats.abs_of_neg += 1
            minimum, maximum = self.intervalframe.minvalues[arg0arg0], self.intervalframe.maxvalues[arg0arg0]
            return self.opt_abs(arg0arg0, minimum, maximum)
        minimum, maximum = self.intervalframe._abs(arg0minimum, arg0maximum)
        return self.opt_default(OPS.abs, minimum, maximum, arg0)

    def opt_square(self, arg0, arg0minimum, arg0maximum):
        func, arg0arg0, _ = self.resultops.get_func_and_args(arg0)
        if OPS.mask(func) == OPS.neg:
            stats.square_of_neg += 1
            minimum, maximum = self.intervalframe.minvalues[arg0arg0], self.intervalframe.maxvalues[arg0arg0]
            return self.opt_square(arg0arg0, minimum, maximum)
        minimum, maximum = self.intervalframe._square(arg0minimum, arg0maximum)
        return self.opt_default(OPS.square, minimum, maximum, arg0)

    def opt_sqrt(self, arg0, arg0minimum, arg0maximum):
        minimum, maximum = self.intervalframe._sqrt(arg0minimum, arg0maximum)
        return self.opt_default(OPS.sqrt, minimum, maximum, arg0)

    def opt_neg(self, arg0, arg0minimum, arg0maximum):
        func, arg0arg0, _ = self.resultops.get_func_and_args(arg0)
        if OPS.mask(func) == OPS.neg:
            stats.neg_neg += 1
            return arg0arg0
        minimum, maximum = self.intervalframe._neg(arg0minimum, arg0maximum)
        return self.opt_default(OPS.neg, minimum, maximum, arg0)

    @symmetric
    def opt_add(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum == arg0maximum == 0:
            stats.add0 += 1
            return arg1
        return -1

    def opt_sub(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0 == arg1:
            stats.sub_self += 1
            return self.newconst(0.0)
        if arg0minimum == arg0maximum == 0:
            stats.zero_sub += 1
            return self.opt_neg(arg1, arg1minimum, arg1maximum)
        if arg1minimum == arg1maximum == 0:
            stats.sub_zero += 1
            return arg0
        minimum, maximum = self.intervalframe._sub(arg0minimum, arg0maximum, arg1minimum, arg1maximum)
        return self.opt_default(OPS.sub, minimum, maximum, arg0, arg1)

    @symmetric
    def opt_min(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0maximum < arg1minimum:
            stats.min_range += 1
            return arg0
        if arg0 == arg1:
            stats.min_self += 1
            return arg0
        func, arg0arg0, arg0arg1 = self.resultops.get_func_and_args(arg0)
        if OPS.mask(func) == OPS.min:
            # min(a, min(a, b)) -> min(a, b)
            if arg0arg0 == arg1 or arg0arg1 == arg1:
                stats.min_min_self += 1
                return arg0
        return -1

    @symmetric
    def opt_max(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0minimum > arg1maximum:
            stats.max_range += 1
            return arg0
        if arg0 == arg1:
            stats.max_self += 1
            return arg0
        func, arg0arg0, arg0arg1 = self.resultops.get_func_and_args(arg0)
        if OPS.mask(func) == OPS.max:
            # max(a, max(a, b)) -> max(a, b)
            if arg0arg0 == arg1 or arg0arg1 == arg1:
                stats.max_max_self += 1
                return arg0
        return -1

    @symmetric
    def opt_mul(self, arg0, arg1, arg0minimum, arg0maximum, arg1minimum, arg1maximum):
        if arg0 == arg1:
            stats.mul_self += 1
            return self.opt_square(arg0, arg0minimum, arg0maximum)
        if arg0minimum == arg0maximum:
            if arg0minimum == 0.0:
                stats.mul0 += 1
                return self.newconst(0.0)
            if arg0maximum == 1.0:
                stats.mul1 += 1
                return arg1
            if arg0maximum == -1.0:
                stats.mul_neg1 += 1
                return self.opt_neg(arg1, arg1minimum, arg1maximum)
        return -1

    def dce(self, final_op):
        ops = self.resultops
        def mark_alive(new_positions, arg):
            if new_positions[arg] == -1:
                new_positions[arg] = 0
        # reuse no longer used opreplacements lists
        new_positions = self.opreplacements
        for i in range(final_op):
            new_positions[i] = -1
        new_positions[final_op] = 0
        alive_ops = 0
        alive_consts = 0
        for index in range(final_op, -1, -1):
            if new_positions[index] < 0:
                continue
            alive_ops += 1
            func, arg0, arg1 = ops.get_func_and_args(index)
            if func == OPS.const:
                alive_consts += 1
                continue
            numargs = OPS.num_args(func)
            if numargs == 0:
                pass
            else:
                if numargs == 1:
                    mark_alive(new_positions, arg0)
                else:
                    mark_alive(new_positions, arg0)
                    mark_alive(new_positions, arg1)
        index = 0

        # fiddly, but saves time: move the operations in the ops ProgramBuilder in place
        ops.reset()
        for op in range(final_op + 1):
            if new_positions[index] >= 0:
                func = ops.funcs[op]
                arg0 = ops.arguments[op*2]
                if func == OPS.const:
                    newop = ops.add_const(ops.consts[arg0])
                else:
                    arg1 = ops.arguments[op*2 + 1]
                    numargs = OPS.num_args(func)
                    if numargs == 0:
                        arg0 = arg1 = 0
                    elif numargs == 1:
                        arg0 = new_positions[arg0]
                        arg1 = 0
                    elif numargs == 2:
                        arg0 = new_positions[arg0]
                        arg1 = new_positions[arg1]
                    newop = ops.add_op(func, arg0, arg1)
                new_positions[index] = newop
            index += 1
        self.resultops = None
        return ops

def convert_to_shortcut(resultops, op):
    func = OPS.mask(resultops.get_func(op))
    if func == OPS.min:
        return convert_check_negative(resultops, op)
    elif func == OPS.max:
        return convert_check_positive(resultops, op)
    return 0

def convert_check_negative(resultops, op):
    converted = 0
    while 1:
        func = OPS.mask(resultops.get_func(op))
        if func == OPS.const:
            break
        resultops.funcs[op] = OPS.add_flag(func, OPS.RETURN_IF_NEG)
        if func == OPS.min:
            converted += 1
            op, arg1 = resultops.get_args(op)
            converted += convert_check_negative(resultops, arg1)
            continue
        break
    return converted

def convert_check_positive(resultops, op):
    converted = 0
    while 1:
        func = OPS.mask(resultops.get_func(op))
        if func == OPS.const:
            break
        resultops.funcs[op] = OPS.add_flag(func, OPS.RETURN_IF_POS)
        if func == OPS.max:
            converted += 1
            op, arg1 = resultops.get_args(op)
            converted += convert_check_positive(resultops, arg1)
            continue
        break
    return converted


def work_backwards(resultops, result, minvalues, maxvalues, for_direct=False):
    #if not objectmodel.we_are_translated():
    #    for op in resultops:
    #        print(resultops.op_to_str(op), minvalues[op], maxvalues[op])
    def check_gt(resultops, op, minvalues, maxvalues, check_gt, val=0.0):
        while 1:
            func, arg0, arg1 = resultops.get_func_and_args(op)
            #if not objectmodel.we_are_translated():
            #    print("round!", OPS.char_to_name(func), "_%x" % op, minvalues[op], maxvalues[op])
            if func == OPS.max:
                narg0 = check_gt(resultops, arg0, minvalues, maxvalues, check_gt, val)
                if narg0 != arg0:
                    resultops.arguments[op * 2 + 0] = narg0
                narg1 = check_gt(resultops, arg1, minvalues, maxvalues, check_gt, val)
                if narg1 != arg1:
                    resultops.arguments[op * 2 + 1] = narg1
            if func == OPS.min:
                if minvalues[arg0] > val:
                    op = arg1
                    continue
                if minvalues[arg1] > val:
                    op = arg0
                    continue
            break
        return op
    otherop = check_gt(resultops, result, minvalues, maxvalues, check_gt)
    #if result != otherop:
        #if not objectmodel.we_are_translated():
        #    print("SHORTENED! by", result - otherop, "to", "_%x" % otherop)
    stats.backwards_shortening += result - otherop
    if for_direct:
        converted = convert_to_shortcut(resultops, otherop)
    return otherop
