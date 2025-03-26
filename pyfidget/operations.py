class Opnums(object):
    RETURN_IF_NEG = 0x80
    RETURN_IF_POS = 0x40

    def get(self, name):
        return opname_to_char[name]

    def char_to_name(self, char):
        res = opnames[self.mask_to_int(char)]
        if self.should_return_if_neg(char):
            res += " return_if_neg"
        if self.should_return_if_pos(char):
            res += " return_if_pos"
        return res

    def num_args(self, char):
        return numargs[self.mask_to_int(char)]

    def is_symmetric(self, char):
        return is_symmetric[self.mask_to_int(char)]

    def mask_to_int(self, char):
        return ord(char) & 0x3f

    def mask(self, char):
        return chr(ord(char) & 0x3f)

    def add_flag(self, char, flag):
        return chr(ord(char) | flag)

    def should_return_if_neg(self, char):
        return ord(char) & self.RETURN_IF_NEG

    def should_return_if_pos(self, char):
        return ord(char) & self.RETURN_IF_POS


opname_to_char = {}
opnames = []
numargs = []
is_symmetric = []

def add_op(name, num_args, symmetric=False):
    opname_to_char[name] = chr(len(opname_to_char))
    opnames.append(name)
    numargs.append(num_args)
    is_symmetric.append(symmetric)

add_op('var-x', 0)
add_op('var-y', 0)
add_op('var-z', 0)
add_op('const', 1)
add_op('square', 1)
add_op('sqrt', 1)
add_op('exp', 1)
add_op('neg', 1)
add_op('abs', 1)
add_op('add', 2, symmetric=True)
add_op('sub', 2)
add_op('mul', 2, symmetric=True)
add_op('max', 2, symmetric=True)
add_op('min', 2, symmetric=True)

OPS = Opnums()
for name, char in opname_to_char.iteritems():
    setattr(OPS, name.replace('-', '_'), char)
