import math

class Evaluable(object):
    def add(self, other):
        raise NotImplementedError()
    
    def sub(self, other):
        raise NotImplementedError()
    
    def mul(self, other):
        raise NotImplementedError()
    
    def max(self, other):
        raise NotImplementedError()
    
    def min(self, other):
        raise NotImplementedError()
    
    def square(self):
        raise NotImplementedError()
    
    def sqrt(self):
        raise NotImplementedError()
    
    def exp(self):
        raise NotImplementedError()
    
    def make_constant(self, value):
        raise NotImplementedError()

class Float(Evaluable):
    def __init__(self, value):
        self.value = value

    def add(self, other):
        return Float(self.value + other.value)
    
    def sub(self, other):
        return Float(self.value - other.value)
    
    def mul(self, other):
        return Float(self.value * other.value)
    
    def max(self, other):
        return Float(max(self.value, other.value))
    
    def min(self, other):
        return Float(min(self.value, other.value))
    
    def square(self):
        return Float(self.value * self.value)
    
    def sqrt(self):
        return Float(math.sqrt(self.value))
    
    def exp(self):
        return Float(math.exp(self.value))

    def make_constant(self, value):
        return Float(value)
    
    def __repr__(self):
        return str(self.value)


class FloatRange(Evaluable):
    def __init__(self, minimum, maximum):
        assert minimum <= maximum
        self.minimum = minimum
        self.maximum = maximum
    
    def add(self, other):
        return FloatRange(self.minimum + other.minimum, self.maximum + other.maximum)
    
    def sub(self, other):
        return FloatRange(self.minimum - other.maximum, self.maximum - other.minimum)
    
    def mul(self, other):
        return FloatRange(min(self.minimum * other.minimum, self.minimum * other.maximum, self.maximum * other.minimum, self.maximum * other.maximum), max(self.minimum * other.minimum, self.minimum * other.maximum, self.maximum * other.minimum, self.maximum * other.maximum))
    
    def max(self, other):
        return FloatRange(max(self.minimum, other.minimum), max(self.maximum, other.maximum))
    
    def min(self, other):
        return FloatRange(min(self.minimum, other.minimum), min(self.maximum, other.maximum))
    
    def square(self):
        if self.minimum >= 0:
            return FloatRange(self.minimum * self.minimum, self.maximum * self.maximum)
        elif self.maximum <= 0:
            return FloatRange(self.maximum * self.maximum, self.minimum * self.minimum)
        else:
            return FloatRange(0, max(self.minimum * self.minimum, self.maximum * self.maximum))
    
    def sqrt(self):
        assert 0, 'trickier'

    def exp(self):
        return FloatRange(math.exp(self.minimum), math.exp(self.maximum))

    def make_constant(self, value):
        return FloatRange(value, value)

    def __repr__(self):
        return "[%s, %s]" % (self.minimum, self.maximum)

    def contains(self, value):
        return self.minimum <= value <= self.maximum