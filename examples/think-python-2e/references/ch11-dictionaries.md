# Chapter 11: Dictionaries

Source pages 125-136 of the PDF.

## When to use

Open this file for questions about: dictionary, global variable, fibonacci, lookup, homophone, keys, key-value, graph.

## Sections

This chapter presents another built-in type called a dictionary. Dictionaries are one of Python’s best features; they are the building blocks of many efficient and elegant algorithms.

### 11.1 A dictionary is a mapping

A dictionary is like a list, but more general. In a list, the indices have to be integers; in a dictionary they can be (almost) any type.

### 11.2 Dictionary as a collection of counters

Suppose you are given a string and you want to count how many times each letter appears. There are several ways you could do it:

### 11.3 Looping and dictionaries

If you use a dictionary in a for statement, it traverses the keys of the dictionary. For example, print_hist prints each key and the corresponding value:

### 11.4 Reverse lookup

Given a dictionary d and a key k, it is easy to find the corresponding value v = d[k]. This operation is called a lookup.

### 11.5 Dictionaries and lists

Lists can appear as values in a dictionary. For example, if you are given a dictionary that maps from letters to frequencies, you might want to invert it; that is, create a dictionary that maps from frequencies to letters.

### 11.6 Memos

If you played with the fibonacci function from Section 6.7, you might have noticed that the bigger the argument you provide, the longer the function takes to run. Furthermore, the run time increases quickly.

### 11.7 Global variables

In the previous example, known is created outside the function, so it belongs to the special frame called __main__. Variables in __main__ are sometimes called global because they can be accessed from any function.

### 11.8 Debugging

As you work with bigger datasets it can become unwieldy to debug by printing and checking the output by hand. Here are some suggestions for debugging large datasets:

### 11.10 Exercises

Exercise 11.1. Write a function that reads the words in words.txt and stores them as keys in a dictionary.

## Key definitions

- A dictionary contains a collection of indices, which are called keys, and a collection of values.
- The association of a key and a value is called a key-value pair or sometimes an item.
- This operation is called a lookup.
- Here is a function that takes a value and returns the first key that maps to that value:
- Here is a function that inverts a dictionary:
- I mentioned earlier that a dictionary is implemented using a hashtable and that means that the keys have to be hashable.
- A hash is a function that takes a value (of any kind) and returns an integer.
- Count how many times fibonacci(0) and fibonacci(1) are called.
- A previously computed value that is stored for later use is called a memo.
- known is a dictionary that keeps track of the Fibonacci numbers we already know.
- Whenever fibonacci is called, it checks known.
- If a global variable refers to a mutable value, you can modify the value without declaring the variable:

## Worked examples

From *A dictionary is a mapping*: Because dict is the name of a built-in function, you should avoid using it as a variable name.

```
>>> eng2sp = dict()
>>> eng2sp
{}
```

From *Dictionary as a collection of counters*: Here is what the code might look like:

```
def histogram(s):
    d = dict()
    for c in s:
        if c not in d:
            d[c] = 1
        else:
            d[c] += 1
    return d
```

From *Looping and dictionaries*: For example, print_hist prints each key and the corresponding value:

```
def print_hist(h):
    for c in h:
        print(c, h[c])
```

From *Reverse lookup*: Here is a function that takes a value and returns the first key that maps to that value:

```
def reverse_lookup(d, v):
    for k in d:
        if d[k] == v:
            return k
    raise LookupError()
```
