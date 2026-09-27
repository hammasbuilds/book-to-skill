# Chapter 3: Functions

Source pages 39-50 of the PDF.

## When to use

Open this file for questions about: print twice, repeat lyrics, bruce, radians, new function, quotes, math, four.

## Sections

In the context of programming, a function is a named sequence of statements that performs a computation. When you define a function, you specify the name and the sequence of statements.

### 3.1 Function calls

We have already seen one example of a function call:

### 3.2 Math functions

Python has a math module that provides most of the familiar mathematical functions. A module is a file that contains a collection of related functions.

### 3.3 Composition

So far, we have looked at the elements of a program—variables, expressions, and statements—in isolation, without talking about how to combine them.

### 3.4 Adding new functions

So far, we have only been using the functions that come with Python, but it is also possible to add new functions. A function definition specifies the name of a new function and the sequence of statements that run when the function is called.

### 3.5 Definitions and uses

Pulling together the code fragments from the previous section, the whole program looks like this:

### 3.6 Flow of execution

To ensure that a function is defined before its first use, you have to know the order statements run in, which is called the flow of execution.

### 3.7 Parameters and arguments

Some of the functions we have seen require arguments. For example, when you call math.sin you pass a number as an argument.

### 3.8 Variables and parameters are local

When you create a variable inside a function, it is local, which means that it only exists inside the function. For example:

### 3.9 Stack diagrams

To keep track of which variables can be used where, it is sometimes useful to draw a stack diagram. Like state diagrams, stack diagrams show the value of each variable, but they also show the function each variable belongs to.

### 3.10 Fruitful functions and void functions

Some of the functions we have used, such as the math functions, return results; for lack of a better name, I call them fruitful functions. Other functions, like print_twice, perform an action but don’t return a value.

### 3.11 Why functions?

It may not be clear why it is worth the trouble to divide a program into functions. There are several reasons:

### 3.12 Debugging

One of the most important skills you will acquire is debugging. Although it can be frustrating, debugging is one of the most intellectually rich, challenging, and interesting parts of programming.

### 3.14 Exercises

Exercise 3.1. Write a function named right_justify that takes a string named s as a parameter and prints the string with enough leading spaces so that the last letter of the string is in column 70 of the display.

## Key definitions

- The expression in parentheses is called the argument of the function.
- A module is a file that contains a collection of related functions.
- This format is called dot notation.
- The variable name radians is a hint that sin and the other trigonometric functions (cos, tan, etc.) take arguments in radians.
- A function definition specifies the name of a new function and the sequence of statements that run when the function is called.
- def is a keyword that indicates that this is a function definition.
- The first line of the function definition is called the header; the rest is called the body.
- The statements inside the function do not run until the function is called, and the function definition generates no output.
- To ensure that a function is defined before its first use, you have to know the order statements run in, which is called the flow of execution.
- Function definitions do not alter the flow of execution of the program, but remember that statements inside the function don’t run until the function is called.
- When the function is called, it prints the value of the parameter (whatever it is) twice.
- The argument is evaluated before the function is called, so in the examples the expressions 'Spam '*4 and math.cos(math.pi) are only evaluated once.

## Worked examples

From *Function calls*: We have already seen one example of a function call:

```
>>> type(42)
<class 'int'>
```

From *Math functions*: If you display the module object, you get some information about it:

```
>>> math
<module 'math' (built-in)>
```

From *Composition*: Any other expression on the left side is a syntax error (we will see exceptions to this rule later).

```
>>> minutes = hours * 60 # right
>>> hours * 60 = minutes # wrong!
SyntaxError: can't assign to operator
```

From *Adding new functions*: Here is an example:

```
def print_lyrics():
    print("I'm a lumberjack, and I'm okay.")
    print("I sleep all night and I work all day.")
```
