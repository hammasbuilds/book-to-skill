# Chapter 8: Strings

Source pages 93-103 of the PDF.

## When to use

Open this file for questions about: index, rotated, fruit, letter, slice, traversal, last character, banana.

## Sections

Strings are not like integers, floats, and booleans. A string is a sequence, which means it is an ordered collection of other values.

### 8.1 A string is a sequence

A string is a sequence of characters. You can access the characters one at a time with the bracket operator:

### 8.2 len

len is a built-in function that returns the number of characters in a string:

### 8.3 Traversal with a for loop

A lot of computations involve processing a string one character at a time. Often they start at the beginning, select each character in turn, do something to it, and continue until the end.

### 8.4 String slices

A segment of a string is called a slice. Selecting a slice is similar to selecting a character:

### 8.5 Strings are immutable

It is tempting to use the [] operator on the left side of an assignment, with the intention of changing a character in a string. For example:

### 8.6 Searching

What does the following function do?

### 8.7 Looping and counting

The following program counts the number of times the letter a appears in a string:

### 8.8 String methods

Strings provide methods that perform a variety of useful operations. A method is similar to a function—it takes arguments and returns a value—but the syntax is different.

### 8.9 The in operator

The word in is a boolean operator that takes two strings and returns True if the first appears as a substring in the second:

### 8.10 String comparison

The relational operators work on strings. To see if two strings are equal:

### 8.11 Debugging

When you use indices to traverse the values in a sequence, it is tricky to get the beginning and end of the traversal right. Here is a function that is supposed to compare two words and return True if one of the words is the reverse of the other, but it contains two errors:

### 8.12 Glossary

object: Something a variable can refer to. For now, you can use “object” and “value”

### 8.13 Exercises

Exercise 8.1. Read the documentation of the string methods at http: // docs. python. org/ 3/ library/ stdtypes. html# string-methods.

## Key definitions

- The expression in brackets is called an index.
- This pattern of processing is called a traversal.
- A segment of a string is called a slice.
- This pattern of computation—traversing a sequence and returning when we find what we are looking for—is called a search.
- A method call is called an invocation; in this case, we would say that we are invoking upper on word.
- The word in is a boolean operator that takes two strings and returns True if the first appears as a substring in the second:
- Here is a function that is supposed to compare two words and return True if one of the words is the reverse of the other, but it contains two errors:
- object: Something a variable can refer to.
- In the movie 2001: A Space Odyssey, the ship computer is called HAL, which is IBM rotated by -1.

## Worked examples

From *A string is a sequence*: You can access the characters one at a time with the bracket operator:

```
>>> fruit = 'banana'
>>> letter = fruit[1]
```

From *len*: len is a built-in function that returns the number of characters in a string:

```
>>> fruit = 'banana'
>>> len(fruit)
6
```

From *Traversal with a for loop*: One way to write a traversal is with a while loop:

```
index = 0
while index < len(fruit):
    letter = fruit[index]
    print(letter)
    index = index + 1
```

From *String slices*: Selecting a slice is similar to selecting a character:

```
>>> s = 'Monty Python'
>>> s[0:5]
'Monty'
>>> s[6:12]
'Python'
```
