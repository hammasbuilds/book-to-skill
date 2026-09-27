# Chapter 4: Case study: interface design

Source pages 51-60 of the PDF.

## When to use

Open this file for questions about: polygon, turtle, circle, segments, angle, window, polyline, circumference.

## Sections

This chapter presents a case study that demonstrates a process for designing functions that work together.

### 4.1 The turtle module

To check whether you have the turtle module, open the Python interpreter and type

### 4.2 Simple repetition

Chances are you wrote something like this:

### 4.3 Exercises

The following is a series of exercises using the turtle module. They are meant to be fun, but they have a point, too.

### 4.4 Encapsulation

The first exercise asks you to put your square-drawing code into a function definition and then call the function, passing the turtle as a parameter. Here is a solution:

### 4.5 Generalization

The next step is to add a length parameter to square. Here is a solution:

### 4.6 Interface design

The next step is to write circle, which takes a radius, r, as a parameter. Here is a simple solution that uses polygon to draw a 50-sided polygon:

### 4.7 Refactoring

When I wrote circle, I was able to re-use polygon because a many-sided polygon is a good approximation of a circle. But arc is not as cooperative; we can’t use polygon or circle to draw an arc.

### 4.8 A development plan

A development plan is a process for writing programs. The process we used in this case study is “encapsulation and generalization”.

### 4.9 docstring

A docstring is a string at the beginning of a function that explains the interface (“doc” is short for “documentation”). Here is an example:

### 4.10 Debugging

An interface is like a contract between a function and a caller. The caller agrees to provide certain parameters and the function agrees to do certain work.

### 4.12 Exercises

Exercise 4.1. Download the code in this chapter from https: // thinkpython. com/ code/ polygon. py.

## Key definitions

- This means that bob refers to an object with type Turtle as defined in module turtle.
- Here is a for statement that draws a square:
- Inside the function, t refers to the same turtle bob, so t.lt(90) has the same effect as bob.lt(90).
- Wrapping a piece of code up in a function is called encapsulation.
- Adding a parameter to a function is called generalization because it makes the function more general: in the previous version, the square is always the same size; in this version it can be any size.
- These are called keyword arguments because they include the parameter names as “keywords” (not to be confused with Python keywords like while and def).
- Here is a simple solution that uses polygon to draw a 50-sided polygon:
- One limitation of this solution is that n is a constant, which means that for very big circles, the line segments are too long, and for small circles, we waste time drawing very small segments.
- This process—rearranging a program to improve interfaces and facilitate code re-use—is called refactoring.
- Sometimes refactoring is a sign that you have learned something.
- A docstring is a string at the beginning of a function that explains the interface (“doc” is short for “documentation”).
- These requirements are called preconditions because they are supposed to be true before the function starts executing.

## Worked examples

From *The turtle module*: To check whether you have the turtle module, open the Python interpreter and type

```
>>> import turtle
>>> bob = turtle.Turtle()
```

From *Simple repetition*: Chances are you wrote something like this:

```
bob.fd(100)
bob.lt(90)

bob.fd(100)
bob.lt(90)

bob.fd(100)
bob.lt(90)

bob.fd(100)
```

From *Encapsulation*: Here is a solution:

```
def square(t):
    for i in range(4):
        t.fd(100)
        t.lt(90)

square(bob)
```

From *Generalization*: Here is a solution:

```
def square(t, length):
    for i in range(4):
        t.fd(length)
        t.lt(90)

square(bob, 100)
```
