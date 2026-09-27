# Chapter A: Debugging

Source pages 215-222 of the PDF.

## When to use

Open this file for questions about: infinite loop, make sure, recursion, suspect, invalid, occurred, causes, model.

## Sections

When you are debugging, you should distinguish among different kinds of errors in order to track them down more quickly:

### A.1 Syntax errors

Syntax errors are usually easy to fix once you figure out what they are. Unfortunately, the error messages are often not helpful.

### A.2 Runtime errors

Once your program is syntactically correct, Python can read it and at least start running it. What could possibly go wrong?

### A.3 Semantic errors

In some ways, semantic errors are the hardest to debug, because the interpreter provides no information about what is wrong. Only you know what the program is supposed to do.

## Key definitions

- Often that means that it is caught in an infinite loop or infinite recursion.
- • If there is a particular loop that you suspect is the problem, add a print statement immediately before the loop that says “entering the loop” and another immediately after that says “exiting the loop”.
- And remember that local variables are local; you cannot refer to them from outside the function where they are defined.
- This can happen if either the number of items does not match or an invalid conversion is called for.
- If an AttributeError indicates that an object has NoneType, that means that it is None.

## Worked examples

From *Runtime errors*: For example:

```
while x > 0 and y < 0 :
    # do something to x
    # do something to y

    print('x: ', x)
    print('y: ', y)
    print("condition: ", (x > 0 and y < 0))
```

From *Semantic errors*: This can be rewritten as:

```
neighbor = self.findNeighbor(i)
pickedCard = self.hands[neighbor].popCard()
self.hands[i].addCard(pickedCard)
```
