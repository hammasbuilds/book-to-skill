# Chapter 2: Variables, expressions and statements

Source pages 31-37 of the PDF.

## When to use

Open this file for questions about: script, interactive mode, spam, precedence, illegal, semantic, comments, syntax error.

## Sections

One of the most powerful features of a programming language is the ability to manipulate variables. A variable is a name that refers to a value.

### 2.1 Assignment statements

An assignment statement creates a new variable and gives it a value:

### 2.2 Variable names

Programmers generally choose names for their variables that are meaningful—they document what the variable is used for.

### 2.3 Expressions and statements

An expression is a combination of values, variables, and operators. A value all by itself is considered an expression, and so is a variable, so the following are all legal expressions:

### 2.4 Script mode

So far we have run Python in interactive mode, which means that you interact directly with the interpreter. Interactive mode is a good way to get started, but if you are working with more than a few lines of code, it can be clumsy.

### 2.5 Order of operations

When an expression contains more than one operator, the order of evaluation depends on the order of operations. For mathematical operators, Python follows mathematical convention.

### 2.6 String operations

In general, you can’t perform mathematical operations on strings, even if the strings look like numbers, so the following are illegal:

### 2.7 Comments

As programs get bigger and more complicated, they get more difficult to read. Formal languages are dense, and it is often difficult to look at a piece of code and figure out what it is doing, or why.

### 2.8 Debugging

Three kinds of errors can occur in a program: syntax errors, runtime errors, and semantic errors. It is useful to distinguish between them in order to track them down more quickly.

### 2.10 Exercises

Exercise 2.1. Repeating my advice from the previous chapter, whenever you learn a new feature, you should try it out in interactive mode and make errors on purpose to see what goes wrong.

## Key definitions

- A variable is a name that refers to a value.
- This kind of figure is called a state diagram because it shows what state each of the variables is in (think of it as the variable’s state of mind).
- When you type an expression at the prompt, the interpreter evaluates it, which means that it finds the value of the expression.
- A statement is a unit of code that has an effect, like creating a variable or displaying a value.
- The second line is a print statement that displays the value of n.
- When you type a statement, the interpreter executes it, which means that it does whatever the statement says.
- So far we have run Python in interactive mode, which means that you interact directly with the interpreter.
- On the other hand, there is a significant way in which string concatenation and repetition are different from integer addition and multiplication.
- These notes are called comments, and they start with the # symbol:
- Syntax error: “Syntax” refers to the structure of a program and the rules about that structure.

## Worked examples

From *Assignment statements*: An assignment statement creates a new variable and gives it a value:

```
>>> message = 'And now for something completely different'
>>> n = 17
>>> pi = 3.1415926535897932
```

From *Variable names*: If you give a variable an illegal name, you get a syntax error:

```
>>> 76trombones = 'big parade'
SyntaxError: invalid syntax
>>> more@ = 1000000
SyntaxError: invalid syntax
>>> class = 'Advanced Theoretical Zymurgy'
SyntaxError: invalid syntax
```

From *Expressions and statements*: A value all by itself is considered an expression, and so is a variable, so the following are all legal expressions:

```
>>> 42
42
>>> n
17
>>> n + 25
42
```

From *Script mode*: For example, if you are using Python as a calculator, you might type

```
>>> miles = 26.2
>>> miles * 1.61
42.182
```
