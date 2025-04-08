playing around with an rpython version of https://github.com/mkeeter/fidget

# Solving the Prospero Challenge in RPython

Recently I had a lot of fun playing with the [Prospero Challenge](https://www.mattkeeter.com/projects/prospero/) by [Matt Keeter](https://www.mattkeeter.com/).
The challenge is to render a 1024x1024 of a quote from The Tempest by Shakespeare. The input is a mathematical formula with 7866 operations. What made the challenge particularly
enticing for me personally was the fact that the formula is basically a trace in SSA-form – a linear sequence of operations, where every variable is assinged exactly once. The challenge is to evaluate the formula as fast as possible.
I tried a number of ideas how to speed up execution and will talk about them in this somewhat meandering post.

## Input program

The input program is a sequence of operations, like this:

```
_0 const 2.95
_1 var-x
_2 const 8.13008
_3 mul _1 _2
_4 add _0 _3
_5 const 3.675
_6 add _5 _3
_7 neg _6
_8 max _4 _7
...
```

The first column is the name of the result variable, the second column is the operation, and the rest are the arguments to the operation. The `var-x` is a special operation that
returns the x-coordinate of the pixel being rendered, and equivalently for `var-y` the y-coordinate. The sign of the result gives the color of the pixel, the absolute value is not important.

## Using Quadtrees to evaluate the picture

The approach that Matt describes in his really excellent [talk]() is to recursively subdivide the image into quadrants, and evaluate the formula in each quadrant. For every quadrant you can simplify the formula by doing a range analysis. At the bottom of the recursion you either reach a square where the range analysis reveals that the sign for all pixels is determined, then you can fill in all the pixels of the quadrant. Or you can evaluate the (now much simpler) formula in the quadrant by executing it for every pixel.

This is an interesting use case of compiler/optimization techniques because it requires the optimizer to execute really quickly, since it is an essential part of the performance of the algorithm.

## Applying the toy optimizer pattern

The first thing I did was to implement a simple interpreter for the SSA-form input program. The interpreter is a simple register machine, where every operation is executed in order. The result of the operation is stored into a list of results, and the next operation is executed. This was the slow baseline implementation of the interpreter but it's very useful to compare the optimized versions against.

To implement the quadtree recursion is straightforward. Since the program has no control flow, I could directly apply the [Toy
Optimizer](https://pypy.org/categories/toy-optimizer.html) approach. The interval analysis is an [abstract interpretation](https://pypy.org/posts/2024/08/toy-knownbits.html) of the operations. The optimizer does a sequential forward pass over the input program. For every operation, the output interval is computed. The optimizer also performs optimizations based on the computed intervals, which helps in reducing the number of operations executed (I'll talk about this later).

To make sure that my interval computation is correct, I implement a hypothesis-based property based test. It checks the abstract transfer functions of the interval domain for soundness. It does so by generating random concrete input values for an operation, random intervals that surround the random concrete values, then performs the concrete operation to get the concrete output, and checks that the abstract transfer function applied to the input intervals gives an interval that contains the concrete output.



no machine code generation, simply interpret resulting traces

implemented in RPython so that I compile the Python code to C to stand some kind of chance.

## Interval analysis as abstract interpretation

Abstract interpretation based on intervals for smaller parts of the image.

random testing for the soundness of the abstract domain transfer functions

example

## Peephole rewrites

optimizer: random tests by generating random operations, optimizing, comparing input and output before and after optimization

tried to add a bunch of extra optimization rules but they mostly seem not to help

main workhorse is min and max shortcuts based on interval, like in Fidget.
max is 84% of all rewrites, min 12%, together 96%. Remaining 4% of rewrites are:

```
--x => x, 4.65%
(-x)**2 => x ** 2, 0.99%
min(x, x) => x, 20.86%
min(x, min(x, y)) =>  min(x, y), 52.87%
max(x, x) => x, 16.40%
max(x, max(x, y)) => max(x, y), 4.23%
```

However, the optimizations actually make things slower, because they trigger so
rarely (more time spent in optimizer, less with no interpreter win to show for
it).


## Dead code elimination

dead code elimination by doing a single backwards pass

no register allocation, didn't get to it and wasn't too interested

## Demanded Information Optimization

LLVM has an information called 'Demanded bits': 
a backwards analysis to notice that certain bits of an expression aren't being
used in the result further on. `<some complicated expression> & 0xff` need to
compute the expression only in the last byte

for fidget: to find out the value of a pixel you don't actually care about the
full value of the expression, only its sign. this makes it possible to simplify
certain min/max operations further. example:

```
x var-x     # [0.1, 1]
y var-y     # [-1, 1]
out min x y # [-1, 1]
```

can be "optimized" to `y var-y`. the numerical value will be wrong, but the sign is still correct.

Similarly, this code:

```
x var-x        # [1, 100]
y var-y        # [-10, 10]
z var-z        # [-100, 100]
out min x y    # [-10, 10]
out2 max z out # [-10, 100]
```

can be optimized to this:

y var-y
z var-z
out max z y

in my quick experiment, this lets me directly remove 25% of all operations in prospero, at the various levels of my octree.

## C implementation

wanted to be faster still, rpython hard to control low level aspects, so rewrote things in C.

mostly to have fun, wanted to try out some things I never had:

- musttail
- SIMD (using Clang's `ext_vector_type`), processing eight pixels at once
- packing the operations struct very efficiently (struct with 8 bytes, by
  limiting maximum number of operations to 65536)

not studied the effects of any of these super carefully though, maybe some of them are useless.


