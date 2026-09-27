# Chapter 7: Iteration

Source pages 85-92 of the PDF.

## When to use

Open this file for questions about: estimate, equality, square root, loop, update, prove, reassignment, eval.

## Sections

This chapter is about iteration, which is the ability to run a block of statements repeatedly. We saw a kind of iteration, using recursion, in Section 5.8.

### 7.1 Reassignment

As you may have discovered, it is legal to make more than one assignment to the same variable. A new assignment makes an existing variable refer to a new value (and stop referring to the old value).

### 7.2 Updating variables

A common kind of reassignment is an update, where the new value of the variable depends on the old.

### 7.3 The while statement

Computers are often used to automate repetitive tasks. Repeating identical or similar tasks without making errors is something that computers do well and people do poorly.

### 7.4 break

Sometimes you don’t know it’s time to end a loop until you get half way through the body. In that case you can use the break statement to jump out of the loop.

### 7.5 Square roots

Loops are often used in programs that compute numerical results by starting with an approximate answer and iteratively improving it.

### 7.6 Algorithms

Newton’s method is an example of an algorithm: it is a mechanical process for solving a category of problems (in this case, computing square roots).

### 7.7 Debugging

As you start writing bigger programs, you might find yourself spending more time debugging. More code means more chances to make an error and more places for bugs to hide.

### 7.8 Glossary

reassignment: Assigning a new value to a variable that already exists.

### 7.9 Exercises

Exercise 7.1. Copy the loop from Section 7.5 and encapsulate it in a function called mysqrt that takes a as a parameter, chooses a reasonable value of x, and returns an estimate of the square root of a.

## Key definitions

- A new assignment makes an existing variable refer to a new value (and stop referring to the old value).
- Updating a variable by adding 1 is called an increment; subtracting 1 is called a decrement.
- Here is a version of countdown that uses a while statement:
- This type of flow is called a loop because the third step loops back around to the top.
- Otherwise the loop will repeat forever, which is called an infinite loop.
- Here is a loop that starts with an initial estimate, x, and improves it until it stops changing:

## Worked examples

From *Reassignment*: A new assignment makes an existing variable refer to a new value (and stop referring to the old value).

```
>>> x = 5
>>> x
5
>>> x = 7
>>> x
7
```

From *Updating variables*: If you try to update a variable that doesn’t exist, you get an error, because Python evaluates the right side before it assigns a value to x:

```
>>> x = x + 1
NameError: name 'x' is not defined
```

From *The while statement*: Here is a version of countdown that uses a while statement:

```
def countdown(n):
    while n > 0:
        print(n)
        n = n - 1
    print('Blastoff!')
```

From *break*: You could write:

```
while True:
    line = input('> ')
    if line == 'done':
        break
    print(line)

print('Done!')
```
