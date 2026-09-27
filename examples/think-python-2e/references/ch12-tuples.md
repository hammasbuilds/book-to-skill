# Chapter 12: Tuples

Source pages 137-146 of the PDF.

## When to use

Open this file for questions about: tuple assignment, zip object, telephone, structshape, reducible, iterator, lists, sequences.

## Sections

This chapter presents one more built-in type, the tuple, and then shows how lists, dictionaries, and tuples work together. I also present a useful feature for variable-length argument lists, the gather and scatter operators.

### 12.1 Tuples are immutable

A tuple is a sequence of values. The values can be any type, and they are indexed by integers, so in that respect tuples are a lot like lists.

### 12.2 Tuple assignment

It is often useful to swap the values of two variables. With conventional assignments, you have to use a temporary variable.

### 12.3 Tuples as return values

Strictly speaking, a function can only return one value, but if the value is a tuple, the effect is the same as returning multiple values. For example, if you want to divide two integers and compute the quotient and remainder, it is inefficient to compute x//y and then x%y.

### 12.4 Variable-length argument tuples

Functions can take a variable number of arguments. A parameter name that begins with * gathers arguments into a tuple.

### 12.5 Lists and tuples

zip is a built-in function that takes two or more sequences and interleaves them. The name of the function refers to a zipper, which interleaves two rows of teeth.

### 12.6 Dictionaries and tuples

Dictionaries have a method called items that returns a sequence of tuples, where each tuple is a key-value pair.

### 12.7 Sequences of sequences

I have focused on lists of tuples, but almost all of the examples in this chapter also work with lists of lists, tuples of tuples, and tuples of lists. To avoid enumerating the possible combinations, it is sometimes easier to talk about sequences of sequences.

### 12.8 Debugging

Lists, dictionaries and tuples are examples of data structures; in this chapter we are starting to see compound data structures, like lists of tuples, or dictionaries that contain tuples as keys and lists as values. Compound data structures are useful, but they are prone to what I call shape errors; that is, errors caused when a data structure has the wrong type, size, or structure.

### 12.9 Glossary

tuple: An immutable sequence of elements.

### 12.10 Exercises

Exercise 12.1. Write a function called most_frequent that takes a string and prints the letters in decreasing order of frequency.

## Key definitions

- This statement makes a new tuple and then makes t refer to it.
- The name of the function refers to a zipper, which interleaves two rows of teeth.
- The result is a zip object that knows how to iterate through the pairs.

## Worked examples

From *Tuples are immutable*: To create a tuple with a single element, you have to include a final comma:

```
>>> t1 = 'a',
>>> type(t1)
<class 'tuple'>
```

From *Tuple assignment*: For example, to swap a and b:

```
>>> temp = a
>>> a = b
>>> b = temp
```

From *Tuples as return values*: You can store the result as a tuple:

```
>>> t = divmod(7, 3)
>>> t
(2, 1)
```

From *Variable-length argument tuples*: For example, printall takes any number of arguments and prints them:

```
def printall(*args):
    print(args)
```
