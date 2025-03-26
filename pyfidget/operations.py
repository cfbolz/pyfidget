class Opnums(object):
    RETURN_IF_NEG = 0x80

    def get(self, name):
        return opname_to_char[name]

    def char_to_name(self, char):
        return opnames[self.mask_to_int(char)] + ("_ret_if_neg" if ord(char) & 0x80 else "")

    def num_args(self, char):
        return numargs[self.mask_to_int(char)]

    def is_symmetric(self, char):
        return is_symmetric[self.mask_to_int(char)]

    def mask_to_int(self, char):
        return ord(char) & 0x7f

    def mask(self, char):
        return chr(ord(char) & 0x7f)

    def should_return_if_neg(self, char):
        return ord(char) & 0x80

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
add_op('add', 2, symmetric=True)
add_op('sub', 2)
add_op('mul', 2, symmetric=True)
add_op('max', 2, symmetric=True)
add_op('min', 2, symmetric=True)
add_op('square', 1)
add_op('sqrt', 1)
add_op('exp', 1)
add_op('neg', 1)
add_op('abs', 1)
add_op('const', 1)

OPS = Opnums()
for name, char in opname_to_char.iteritems():
    setattr(OPS, name.replace('-', '_'), char)
