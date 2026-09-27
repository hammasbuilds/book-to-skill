# Chapter 1: The way of the program

Source pages 23-30 of the PDF.

## When to use

Open this file for questions about: formal, natural languages, tokens, hello world, basic, ambiguity, instructions, interpreter.

## Sections

The goal of this book is to teach you to think like a computer scientist. This way of thinking combines some of the best features of mathematics, engineering, and natural science.

### 1.1 What is a program?

A program is a sequence of instructions that specifies how to perform a computation. The computation might be something mathematical, such as solving a system of equations or finding the roots of a polynomial, but it can also be a symbolic computation, such as searching and replacing text in a document or something graphical, like processing an image or playing a video.

### 1.2 Running Python

One of the challenges of getting started with Python is that you might have to install Python and related software on your computer. If you are familiar with your operating system, and especially if you are comfortable with the command-line interface, you will have no trouble installing Python.

### 1.3 The first program

Traditionally, the first program you write in a new language is called “Hello, World!” because all it does is display the words “Hello, World!”. In Python, it looks like this:

### 1.4 Arithmetic operators

After “Hello, World”, the next step is arithmetic. Python provides operators, which are special symbols that represent computations like addition and multiplication.

### 1.5 Values and types

A value is one of the basic things a program works with, like a letter or a number. Some values we have seen so far are 2, 42.0, and 'Hello, World!

### 1.6 Formal and natural languages

Natural languages are the languages people speak, such as English, Spanish, and French. They were not designed by people (although people try to impose some order on them); they evolved naturally.

### 1.7 Debugging

Programmers make mistakes. For whimsical reasons, programming errors are called bugs and the process of tracking them down is called debugging.

### 1.8 Glossary

problem solving: The process of formulating a problem, finding a solution, and expressing it.

### 1.9 Exercises

Exercise 1.1. It is a good idea to read this book in front of a computer so you can try out the examples as you go.

## Key definitions

- That’s why this chapter is called, “The way of the program”.
- A program is a sequence of instructions that specifies how to perform a computation.
- The Python interpreter is a program that reads and executes Python code.
- The last line is a prompt that indicates that the interpreter is ready for you to enter code.
- Traditionally, the first program you write in a new language is called “Hello, World!” because all it does is display the words “Hello, World!”.
- For example, the notation that mathematicians use is a formal language that is particularly good at denoting relationships among numbers and symbols.
- Formal languages are designed to be nearly or completely unambiguous, which means that any statement has exactly one meaning, regardless of context.
- If I say, “The penny dropped”, there is probably no penny and nothing dropping (this idiom means that someone understood something after a period of confusion).
- For whimsical reasons, programming errors are called bugs and the process of tracking them down is called debugging.
- Learning to debug can be frustrating, but it is a valuable skill that is useful for many activities beyond programming.

## Worked examples

From *Running Python*: When it starts, you should see output like this:

```
Python 3.4.0 (default, Jun 19 2015, 14:20:21)
[GCC 4.8.2] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

From *Arithmetic operators*: The operators +, -, and * perform addition, subtraction, and multiplication, as in the following examples:

```
>>> 40 + 2
42
>>> 43 - 1
42
>>> 6 * 7
42
```

From *Values and types*: If you are not sure what type a value has, the interpreter can tell you:

```
>>> type(2)
<class 'int'>
>>> type(42.0)
<class 'float'>
>>> type('Hello, World!')
<class 'str'>
```
