# Chapter 16: Classes and functions

Source pages 177-182 of the PDF.

## When to use

Open this file for questions about: time object, pure functions, modifiers, prototype, insight, functional, seconds, hour.

## Sections

Now that we know how to create new types, the next step is to write functions that take programmer-defined objects as parameters and return them as results. In this chapter I also present “functional programming style” and two new program development plans.

### 16.1 Time

As another example of a programmer-defined type, we’ll define a class called Time that records the time of day. The class definition looks like this:

### 16.2 Pure functions

In the next few sections, we’ll write two functions that add time values. They demonstrate two kinds of functions: pure functions and modifiers.

### 16.3 Modifiers

Sometimes it is useful for a function to modify the objects it gets as parameters. In that case, the changes are visible to the caller.

### 16.4 Prototyping versus planning

The development plan I am demonstrating is called “prototype and patch”. For each function, I wrote a prototype that performed the basic calculation and then tested it, patching errors along the way.

### 16.5 Debugging

A Time object is well-formed if the values of minute and second are between 0 and 60 (including 0 but not 60) and if hour is positive. hour and minute should be integer values, but we might allow second to have a fraction part.

### 16.6 Glossary

prototype and patch: A development plan that involves writing a rough draft of a program, testing, and correcting errors as they are found.

### 16.7 Exercises

Code examples from this chapter are available from https://thinkpython.com/code/ Time1.py; solutions to the exercises are available from https://thinkpython.com/code/ Time1_soln.py.

## Key definitions

- This is called a pure function because it does not modify any of the objects passed to it as arguments and it has no effect, like displaying a value or getting user input, other than returning a value.
- Functions that work this way are called modifiers.
- The development plan I am demonstrating is called “prototype and patch”.
- Here is a function that converts Times to integers:
- And here is a function that converts an integer to a Time (recall that divmod divides the first argument by the second and returns the quotient and remainder as a tuple).
- Requirements like these are called invariants because they should always be true.

## Worked examples

From *Time*: The class definition looks like this:

```
class Time:
    """Represents the time of day.

    attributes: hour, minute, second
    """
```

From *Pure functions*: Here is a simple prototype of add_time:

```
def add_time(t1, t2):
    sum = Time()
    sum.hour = t1.hour + t2.hour
    sum.minute = t1.minute + t2.minute
    sum.second = t1.second + t2.second
    return sum
```

From *Modifiers*: Here is a rough draft:

```
def increment(time, seconds):
    time.second += seconds

    if time.second >= 60:
        time.second -= 60
        time.minute += 1

    if time.minute >= 60:
        time.minute -= 60
        time.hour += 1
```

From *Prototyping versus planning*: Here is a function that converts Times to integers:

```
def time_to_int(time):
    minutes = time.hour * 60 + time.minute
    seconds = minutes * 60 + time.second
    return seconds
```
