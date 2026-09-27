# Chapter 17: Classes and methods

Source pages 183-192 of the PDF.

## When to use

Open this file for questions about: class, subject, print time, object-oriented, init, invokes, pouch, method.

## Sections

Although we are using some of Python’s object-oriented features, the programs from the last two chapters are not really object-oriented because they don’t represent the relationships between programmer-defined types and the functions that operate on them. The next step is to transform those functions into methods that make the relationships explicit.

### 17.1 Object-oriented features

Python is an object-oriented programming language, which means that it provides features that support object-oriented programming, which has these defining characteristics:

### 17.2 Printing objects

In Chapter 16, we defined a class named Time and in Section 16.1, you wrote a function named print_time:

### 17.3 Another example

Here’s a version of increment (from Section 16.3) rewritten as a method:

### 17.4 A more complicated example

Rewriting is_after (from Section 16.1) is slightly more complicated because it takes two Time objects as parameters. In this case it is conventional to name the first parameter self and the second parameter other:

### 17.5 The init method

The init method (short for “initialization”) is a special method that gets invoked when an object is instantiated. Its full name is __init__ (two underscore characters, followed by init, and then two more underscores).

### 17.6 The __str__ method

__str__ is a special method, like __init__, that is supposed to return a string representation of an object.

### 17.7 Operator overloading

By defining other special methods, you can specify the behavior of operators on programmer-defined types. For example, if you define a method named __add__ for the Time class, you can use the + operator on Time objects.

### 17.8 Type-based dispatch

In the previous section we added two Time objects, but you also might want to add an integer to a Time object. The following is a version of __add__ that checks the type of other and invokes either add_time or increment:

### 17.9 Polymorphism

Type-based dispatch is useful when it is necessary, but (fortunately) it is not always necessary. Often you can avoid it by writing functions that work correctly for arguments with different types.

### 17.10 Debugging

It is legal to add attributes to objects at any point in the execution of a program, but if you have objects with the same type that don’t have the same attributes, it is easy to make mistakes. It is considered a good idea to initialize all of an object’s attributes in the init method.

### 17.11 Interface and implementation

One of the goals of object-oriented design is to make software more maintainable, which means that you can keep the program working when other parts of the system change, and modify the program to meet new requirements.

### 17.12 Glossary

object-oriented language: A language that provides features, such as programmer-defined types and methods, that facilitate object-oriented programming.

### 17.13 Exercises

Exercise 17.1. Download the code from this chapter from https: // thinkpython. com/ code/ Time2. py.

## Key definitions

- Python is an object-oriented programming language, which means that it provides features that support object-oriented programming, which has these defining characteristics:
- This observation is the motivation for methods; a method is a function that is associated with a particular class.
- In this use of dot notation, print_time is the name of the method (again), and start is the object the method is invoked on, which is called the subject.
- By convention, the first parameter of a method is called self, so it would be more common to write print_time like this:
- The init method (short for “initialization”) is a special method that gets invoked when an object is instantiated.
- Changing the behavior of an operator so that it works with programmer-defined types is called operator overloading.
- The following is a version of __add__ that checks the type of other and invokes either add_time or increment:
- This operation is called a type-based dispatch because it dispatches the computation to different methods based on the type of the arguments.
- But there is a clever solution for this problem: the special method __radd__, which stands for “right-side add”.
- Functions that work with several types are called polymorphic.
- One of the goals of object-oriented design is to make software more maintainable, which means that you can keep the program working when other parts of the system change, and modify the program to meet new requirements.
- For objects, that means that the methods a class provides should not depend on how the attributes are represented.

## Worked examples

From *Printing objects*: In Chapter 16, we defined a class named Time and in Section 16.1, you wrote a function named print_time:

```
class Time:
    """Represents the time of day."""

def print_time(time):
    print('%.2d:%.2d:%.2d' % (time.hour, time.minute, time.second))
```

From *Another example*: Here’s a version of increment (from Section 16.3) rewritten as a method:

```
# inside class Time:

    def increment(self, seconds):
        seconds += self.time_to_int()
        return int_to_time(seconds)
```

From *A more complicated example*: In this case it is conventional to name the first parameter self and the second parameter other:

```
# inside class Time:

    def is_after(self, other):
        return self.time_to_int() > other.time_to_int()
```

From *The init method*: An init method for the Time class might look like this:

```
# inside class Time:

    def __init__(self, hour=0, minute=0, second=0):
        self.hour = hour
        self.minute = minute
        self.second = second
```
