# Chapter 6: Fruitful functions

Source pages 73-83 of the PDF.

## When to use

Open this file for questions about: factorial, fibonacci, distance, incremental, palindrome, return statement, recursive, value multiplied.

## Sections

Many of the Python functions we have used, such as the math functions, produce return values. But the functions we’ve written are all void: they have an effect, like printing a value or moving a turtle, but they don’t have a return value.

### 6.1 Return values

Calling the function generates a return value, which we usually assign to a variable or use as part of an expression.

### 6.2 Incremental development

As you write larger functions, you might find yourself spending more time debugging.

### 6.3 Composition

As you should expect by now, you can call one function from within another. As an example, we’ll write a function that takes two points, the center of the circle and a point on the perimeter, and computes the area of the circle.

### 6.4 Boolean functions

Functions can return booleans, which is often convenient for hiding complicated tests inside functions. For example:

### 6.5 More recursion

We have only covered a small subset of Python, but you might be interested to know that this subset is a complete programming language, which means that anything that can be computed can be expressed in this language. Any program ever written could be rewritten using only the language features you have learned so far (actually, you would need a few commands to control devices like the mouse, disks, etc., but that’s all).

### 6.6 Leap of faith

Following the flow of execution is one way to read programs, but it can quickly become overwhelming. An alternative is what I call the “leap of faith”.

### 6.7 One more example

After factorial, the most common example of a recursively defined mathematical function is fibonacci, which has the following definition (see http://en.wikipedia.org/ wiki/Fibonacci_number):

### 6.8 Checking types

What happens if we call factorial and give it 1.5 as an argument?

### 6.9 Debugging

Breaking a large program into smaller functions creates natural checkpoints for debugging. If a function is not working, there are three possibilities to consider:

### 6.10 Glossary

temporary variable: A variable used to store an intermediate value in a complex calculation.

### 6.11 Exercises

Exercise 6.1. Draw a stack diagram for the following program.

## Key definitions

- Code that appears after a return statement, or any other place the flow of execution can never reach, is called dead code.
- But it is syntactically correct, and it runs, which means that you can test it before you make it more complicated.
- Code like that is called scaffolding because it is helpful for building the program but is not part of the final product.
- We have only covered a small subset of Python, but you might be interested to know that this subset is a complete programming language, which means that anything that can be computed can be expressed in this language.
- Accordingly, it is known as the Turing Thesis.
- If we call factorial with the value 3:
- What happens if we call factorial and give it 1.5 as an argument?
- The first option is called the gamma function and it’s a little beyond the scope of this book.
- A palindrome is a word that is spelled the same backward and forward, like “noon” and “redivider”.

## Worked examples

From *Return values*: Calling the function generates a return value, which we usually assign to a variable or use as part of an expression.

```
e = math.exp(1.0)
height = radius * math.sin(radians)
```

From *Incremental development*: Immediately you can write an outline of the function:

```
def distance(x1, y1, x2, y2):
    return 0.0
```

From *Composition*: Encapsulating these steps in a function, we get:

```
def circle_area(xc, yc, xp, yp):
    radius = distance(xc, yc, xp, yp)
    result = area(radius)
    return result
```

From *Boolean functions*: For example:

```
def is_divisible(x, y):
    if x % y == 0:
        return True
    else:
        return False
```
