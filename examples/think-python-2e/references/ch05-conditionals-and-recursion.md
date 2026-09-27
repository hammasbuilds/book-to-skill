# Chapter 5: Conditionals and recursion

Source pages 61-71 of the PDF.

## When to use

Open this file for questions about: koch curve, execution countdown, fermat, form triangle, sticks, floor division, two branches, recursion.

## Sections

The main topic of this chapter is the if statement, which executes different code depending on the state of the program. But first I want to introduce two new operators: floor division and modulus.

### 5.1 Floor division and modulus

The floor division operator, //, divides two numbers and rounds down to an integer. For example, suppose the run time of a movie is 105 minutes.

### 5.2 Boolean expressions

A boolean expression is an expression that is either true or false. The following examples use the operator ==, which compares two operands and produces True if they are equal and False otherwise:

### 5.3 Logical operators

There are three logical operators: and, or, and not. The semantics (meaning) of these operators is similar to their meaning in English.

### 5.4 Conditional execution

In order to write useful programs, we almost always need the ability to check conditions and change the behavior of the program accordingly. Conditional statements give us this ability.

### 5.5 Alternative execution

A second form of the if statement is “alternative execution”, in which there are two possibilities and the condition determines which one runs. The syntax looks like this:

### 5.6 Chained conditionals

Sometimes there are more than two possibilities and we need more than two branches. One way to express a computation like that is a chained conditional:

### 5.7 Nested conditionals

One conditional can also be nested within another. We could have written the example in the previous section like this:

### 5.8 Recursion

It is legal for one function to call another; it is also legal for a function to call itself. It may not be obvious why that is a good thing, but it turns out to be one of the most magical things a program can do.

### 5.9 Stack diagrams for recursive functions

In Section 3.9, we used a stack diagram to represent the state of a program during a function call. The same kind of diagram can help interpret a recursive function.

### 5.10 Infinite recursion

If a recursion never reaches a base case, it goes on making recursive calls forever, and the program never terminates. This is known as infinite recursion, and it is generally not a good idea.

### 5.11 Keyboard input

The programs we have written so far accept no input from the user. They just do the same thing every time.

### 5.12 Debugging

When a syntax or runtime error occurs, the error message contains a lot of information, but it can be overwhelming. The most useful parts are usually:

### 5.14 Exercises

Exercise 5.1. The time module provides a function, also named time, that returns the current Greenwich Mean Time in “the epoch”, which is an arbitrary time used as a reference point.

## Key definitions

- The boolean expression after if is called the condition.
- Statements like this are called compound statements.
- The alternatives are called branches, because they are branches in the flow of execution.
- What happens if we call this function like this?
- A function that calls itself is recursive; the process of executing it is called recursion.
- The bottom of the stack, where n=0, is called the base case.
- This is known as infinite recursion, and it is generally not a good idea.
- If you encounter an infinite recursion by accident, review your function to confirm that there is a base case that does not make a recursive call.
- In Python 2, the same function is called raw_input.
- The sequence \n at the end of the prompt represents a newline, which is a special character that causes a line break.
- (If the sum of two lengths equals the third, they form what is called a “degenerate” triangle.)
- The Koch curve is a fractal that looks something like Figure 5.2.

## Worked examples

From *Floor division and modulus*: Conventional division returns a floating-point number:

```
>>> minutes = 105
>>> minutes / 60
1.75
```

From *Boolean expressions*: The following examples use the operator ==, which compares two operands and produces True if they are equal and False otherwise:

```
>>> 5 == 5
True
>>> 5 == 6
False
```

From *Logical operators*: Any nonzero number is interpreted as True:

```
>>> 42 and True
True
```

From *Conditional execution*: The simplest form is the if statement:

```
if x > 0:
    print('x is positive')
```
