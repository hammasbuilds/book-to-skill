# Chapter 15: Classes and objects

Source pages 169-176 of the PDF.

## When to use

Open this file for questions about: rectangle, circle, embedded, corner, blank, class, point, center.

## Sections

At this point you know how to use functions to organize code and built-in types to organize data. The next step is to learn “object-oriented programming”, which uses programmer-defined types to organize both code and data.

### 15.1 Programmer-defined types

We have used many of Python’s built-in types; now we are going to define a new type. As an example, we will create a type called Point that represents a point in two-dimensional space.

### 15.2 Attributes

You can assign values to an instance using dot notation:

### 15.3 Rectangles

Sometimes it is obvious what the attributes of an object should be, but other times you have to make decisions. For example, imagine you are designing a class to represent rectangles.

### 15.4 Instances as return values

Functions can return instances. For example, find_center takes a Rectangle as an argument and returns a Point that contains the coordinates of the center of the Rectangle:

### 15.5 Objects are mutable

You can change the state of an object by making an assignment to one of its attributes. For example, to change the size of a rectangle without changing its position, you can modify the values of width and height:

### 15.6 Copying

Aliasing can make a program difficult to read because changes in one place might have unexpected effects in another place. It is hard to keep track of all the variables that might refer to a given object.

### 15.7 Debugging

When you start working with objects, you are likely to encounter some new exceptions. If you try to access an attribute that doesn’t exist, you get an AttributeError:

### 15.8 Glossary

class: A programmer-defined type. A class definition creates a new class object.

### 15.9 Exercises

Exercise 15.1. Write a definition for a class named Circle with attributes center and radius, where center is a Point object and radius is a number.

## Key definitions

- The header indicates that the new class is called Point.
- The body is a docstring that explains what the class is for.
- Creating a new object is called instantiation, and the object is an instance of the class.
- When you print an instance, Python tells you what class it belongs to and where it is stored in memory (the prefix 0x means that the following number is in hexadecimal).
- Figure 15.1 is a state diagram that shows the result of these assignments.
- A state diagram that shows an object and its attributes is called an object diagram.
- The variable blank refers to a Point object, which contains two attributes.
- Each attribute refers to a floating-point number.
- The expression blank.x means, “Go to the object blank refers to and get the value of x.” In the example, we assign that value to a variable named x.
- The docstring lists the attributes: width and height are numbers; corner is a Point object that specifies the lower-left corner.
- The expression box.corner.x means, “Go to the object box refers to and select the attribute named corner; then go to that object and select the attribute named x.”
- It is hard to keep track of all the variables that might refer to a given object.

## Worked examples

From *Programmer-defined types*: A class definition looks like this:

```
class Point:
    """Represents a point in 2-D space."""
```

From *Attributes*: You can assign values to an instance using dot notation:

```
>>> blank.x = 3.0
>>> blank.y = 4.0
```

From *Rectangles*: Figure 15.2: Object diagram.

```
class Rectangle:
    """Represents a rectangle.

    attributes: width, height, corner.
    """
```

From *Instances as return values*: For example, find_center takes a Rectangle as an argument and returns a Point that contains the coordinates of the center of the Rectangle:

```
def find_center(rect):
    p = Point()
    p.x = rect.corner.x + rect.width/2
    p.y = rect.corner.y + rect.height/2
    return p
```
