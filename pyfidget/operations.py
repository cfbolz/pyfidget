class Opnums(object):
    def get(self, name):
        return opname_to_char[name]

    def char_to_name(self, char):
        return opnames[ord(char)]

    def num_args(self, char):
        return numargs[ord(char)]

    def is_symmetric(self, char):
        return is_symmetric[ord(char)]

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
