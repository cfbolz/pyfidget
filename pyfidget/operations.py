class Opnums(object):
    def get(self, name):
        return opname_to_char[name]

    def char_to_name(self, char):
        return opnames[ord(char)]

opname_to_char = {}
opnames = []

def add_op(name):
    opname_to_char[name] = chr(len(opname_to_char))
    opnames.append(name)

add_op('var-x')
add_op('var-y')
add_op('var-z')
add_op('add')
add_op('sub')
add_op('mul')
add_op('max')
add_op('min')
add_op('square')
add_op('sqrt')
add_op('exp')
add_op('neg')
add_op('abs')
add_op('const')

OPS = Opnums()
for name, char in opname_to_char.iteritems():
    setattr(OPS, name.replace('-', '_'), char)
