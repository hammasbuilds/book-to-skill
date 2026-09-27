# Chapter 19: The Goodies

Source pages 205-214 of the PDF.

## When to use

Open this file for questions about: generator, defaultdict, named tuple, list comprehensions, element appears, conditional expressions, counters, sets.

## Sections

One of my goals for this book has been to teach you as little Python as possible. When there were two ways to do something, I picked one and avoided mentioning the other.

### 19.1 Conditional expressions

We saw conditional statements in Section 5.4. Conditional statements are often used to choose one of two values; for example:

### 19.2 List comprehensions

In Section 10.7 we saw the map and filter patterns. For example, this function takes a list of strings, maps the string method capitalize to the elements, and returns a new list of strings:

### 19.3 Generator expressions

Generator expressions are similar to list comprehensions, but with parentheses instead of square brackets:

### 19.4 any and all

Python provides a built-in function, any, that takes a sequence of boolean values and returns True if any of the values are True. It works on lists:

### 19.5 Sets

In Section 13.6 I use dictionaries to find the words that appear in a document but not in a word list. The function I wrote takes d1, which contains the words from the document as keys, and d2, which contains the list of words.

### 19.6 Counters

A Counter is like a set, except that if an element appears more than once, the Counter keeps track of how many times it appears. If you are familiar with the mathematical idea of a multiset, a Counter is a natural way to represent a multiset.

### 19.7 defaultdict

The collections module also provides defaultdict, which is like a dictionary except that if you access a key that doesn’t exist, it can generate a new value on the fly.

### 19.8 Named tuples

Many simple objects are basically collections of related values. For example, the Point object defined in Chapter 15 contains two numbers, x and y.

### 19.9 Gathering keyword args

In Section 12.4, we saw how to write a function that gathers its arguments into a tuple:

### 19.11 Exercises

Exercise 19.1. The following is a function that computes the binomial coefficient recursively.

## Key definitions

- The result is a generator object that knows how to iterate through a sequence of values.
- The result is a dictionary that maps from keywords to values:
- The following is a function that computes the binomial coefficient recursively.

## Worked examples

From *Conditional expressions*: Conditional statements are often used to choose one of two values; for example:

```
if x > 0:
    y = math.log(x)
else:
    y = float('nan')
```

From *List comprehensions*: For example, this function takes a list of strings, maps the string method capitalize to the elements, and returns a new list of strings:

```
def capitalize_all(t):
    res = []
    for s in t:
        res.append(s.capitalize())
    return res
```

From *Generator expressions*: Generator expressions are similar to list comprehensions, but with parentheses instead of square brackets:

```
>>> g = (x**2 for x in range(5))
>>> g
<generator object <genexpr> at 0x7f4c45a786c0>
```

From *any and all*: It works on lists:

```
>>> any([False, False, True])
True
```
