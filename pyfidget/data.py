import math

class Evaluable(object):
    _attrs_ = []

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
        assert isinstance(other, Float)
        return Float(self.value + other.value)
    
    def sub(self, other):
        assert isinstance(other, Float)
        return Float(self.value - other.value)
    
    def mul(self, other):
        assert isinstance(other, Float)
        return Float(self.value * other.value)
    
    def max(self, other):
        assert isinstance(other, Float)
        return Float(max(self.value, other.value))
    
    def min(self, other):
        assert isinstance(other, Float)
        return Float(min(self.value, other.value))
    
    def square(self):
        return Float(self.value * self.value)
    
    def sqrt(self):
        return Float(math.sqrt(self.value))
    
    def exp(self):
        return Float(math.exp(self.value))

    def abs(self):
        return Float(abs(self.value))

    def neg(self):
        return Float(-self.value)

    def make_constant(self, value):
        return Float(value)
    
    def __repr__(self):
        return str(self.value)

def min4(a, b, c, d):
    return min(min(a, b), min(c, d))

def max4(a, b, c, d):
    return max(max(a, b), max(c, d))

class FloatRange(Evaluable):
    def __init__(self, minimum, maximum):
        assert minimum <= maximum
        self.minimum = minimum
        self.maximum = maximum
    
    @staticmethod
    def nan():
        return FloatRange(float('nan'), float('nan'))

    def has_nan(self):
        return math.isnan(self.minimum) or math.isnan(self.maximum)

    def add(self, other):
        assert isinstance(other, FloatRange)
        return FloatRange(self.minimum + other.minimum, self.maximum + other.maximum)
    
    def sub(self, other):
        assert isinstance(other, FloatRange)
        return FloatRange(self.minimum - other.maximum, self.maximum - other.minimum)
    
    def mul(self, other):
        assert isinstance(other, FloatRange)
        return FloatRange(min4(self.minimum * other.minimum, self.minimum * other.maximum, self.maximum * other.minimum, self.maximum * other.maximum), max4(self.minimum * other.minimum, self.minimum * other.maximum, self.maximum * other.minimum, self.maximum * other.maximum))
    
    def max(self, other):
        assert isinstance(other, FloatRange)
        return FloatRange(max(self.minimum, other.minimum), max(self.maximum, other.maximum))
    
    def min(self, other):
        assert isinstance(other, FloatRange)
        return FloatRange(min(self.minimum, other.minimum), min(self.maximum, other.maximum))
    
    def square(self):
        if self.minimum >= 0:
            return FloatRange(self.minimum * self.minimum, self.maximum * self.maximum)
        elif self.maximum <= 0:
            return FloatRange(self.maximum * self.maximum, self.minimum * self.minimum)
        else:
            return FloatRange(0, max(self.minimum * self.minimum, self.maximum * self.maximum))
    
    def sqrt(self):
        if self.maximum < 0:
            return FloatRange.nan()
        else:
            return FloatRange(math.sqrt(self.minimum), math.sqrt(self.maximum))

    def exp(self):
        return FloatRange(math.exp(self.minimum), math.exp(self.maximum))

    def abs(self):
        if self.maximum < 0:
            return FloatRange(-self.maximum, -self.minimum)
        elif self.minimum >= 0:
            return self
        else:
            return FloatRange(0, max(-self.minimum, self.maximum))

    def neg(self):
        return FloatRange(-self.maximum, -self.minimum)

    def make_constant(self, value):
        return FloatRange(value, value)

    def __repr__(self):
        return "[%s, %s]" % (self.minimum, self.maximum)

    def contains(self, value):
        return self.minimum <= value <= self.maximum
