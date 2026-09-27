# Chapter 10: Lists

Source pages 111-124 of the PDF.

## When to use

Open this file for questions about: new list, elements, delimiter, slice, interlock, append, refer, modifies.

## Sections

This chapter presents one of Python’s most useful built-in types, lists. You will also learn more about objects and what can happen when you have more than one name for the same object.

### 10.1 A list is a sequence

Like a string, a list is a sequence of values. In a string, the values are characters; in a list, they can be any type.

### 10.2 Lists are mutable

The syntax for accessing the elements of a list is the same as for accessing the characters of a string—the bracket operator. The expression inside the brackets specifies the index.

### 10.3 Traversing a list

The most common way to traverse the elements of a list is with a for loop. The syntax is the same as for strings:

### 10.4 List operations

The + operator concatenates lists:

### 10.5 List slices

The slice operator also works on lists:

### 10.6 List methods

Python provides methods that operate on lists. For example, append adds a new element to the end of a list:

### 10.7 Map, filter and reduce

To add up all the numbers in a list, you can use a loop like this:

### 10.8 Deleting elements

There are several ways to delete elements from a list. If you know the index of the element you want, you can use pop:

### 10.9 Lists and strings

A string is a sequence of characters and a list is a sequence of values, but a list of characters is not the same as a string. To convert from a string to a list of characters, you can use list:

### 10.10 Objects and values

If we run these assignment statements:

### 10.11 Aliasing

If a refers to an object and you assign b = a, then both variables refer to the same object:

### 10.12 List arguments

When you pass a list to a function, the function gets a reference to the list. If the function modifies the list, the caller sees the change.

### 10.13 Debugging

Careless use of lists (and other mutable objects) can lead to long hours of debugging. Here are some common pitfalls and ways to avoid them:

### 10.14 Glossary

list: A sequence of values.

### 10.15 Exercises

You can download solutions to these exercises from https://thinkpython.com/code/ list_exercises.py.

## Key definitions

- The values in a list are called elements or sometimes items.
- A list that contains no elements is called an empty list; you can create one with empty brackets, [].
- isupper is a string method that returns True if the string contains only upper case letters.
- An operation like only_upper is called a filter because it selects some of the elements and filters out the others.
- We know that a and b both refer to a string, but we don’t know whether they refer to the same string.
- In one case, a and b refer to two different objects that have the same value.
- In the second case, they refer to the same object.
- To check whether two variables refer to the same object, you can use the is operator.
- In this example, Python only created one string object, and both a and b refer to it.
- If a refers to an object and you assign b = a, then both variables refer to the same object:
- The association of a variable with an object is called a reference.
- It almost never makes a difference whether a and b refer to the same string or not.

## Worked examples

From *A list is a sequence*: There are several ways to create a new list; the simplest is to enclose the elements in square brackets ([and]):

```
[10, 20, 30, 40]
['crunchy frog', 'ram bladder', 'lark vomit']
```

From *Lists are mutable*: Remember that the indices start at 0:

```
>>> cheeses[0]
'Cheddar'
```

From *Traversing a list*: The syntax is the same as for strings:

```
for cheese in cheeses:
    print(cheese)
```

From *List operations*: The + operator concatenates lists:

```
>>> a = [1, 2, 3]
>>> b = [4, 5, 6]
>>> c = a + b
>>> c
[1, 2, 3, 4, 5, 6]
```
