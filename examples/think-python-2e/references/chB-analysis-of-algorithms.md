# Chapter B: Analysis of Algorithms

Source pages 223-232 of the PDF.

## When to use

Open this file for questions about: linear, order growth, constant time, algorithm, resize, linearmap, sort, performance.

## Sections

This appendix is an edited excerpt from Think Complexity, by Allen B. Downey, also published by O’Reilly Media (2012).

### B.1 Order of growth

Suppose you have analyzed two algorithms and expressed their run times in terms of the size of the input: Algorithm A takes 100 n + 1 steps to solve a problem with size n; Algo- 2 rithm B takes n + n + 1 steps.

### B.2 Analysis of basic Python operations

In Python, most arithmetic operations are constant time; multiplication usually takes longer than addition and subtraction, and division takes even longer, but these run times don’t depend on the magnitude of the operands. Very large integers are an exception; in that case the run time increases with the number of digits.

### B.3 Analysis of search algorithms

A search is an algorithm that takes a collection and a target item and determines whether the target is in the collection, often returning the index of the target.

### B.4 Hashtables

To explain how hashtables work and why their performance is so good, I start with a simple implementation of a map and gradually improve it until it’s a hashtable.

## Key definitions

- 2 2 All functions with the leading term n belong to O(n); they are called quadratic.
- Of course, this means that many different hash values will wrap onto the same index.
- That means that some objects that used to hash into the same LinearMap will get split up (which is what we wanted, right?).

## Worked examples

From *Analysis of basic Python operations*: For example, adding up the elements of a list is linear:

```
total = 0
for x in t:
    total += x
```

From *Hashtables*: The simplest implementation of this interface uses a list of tuples, where each tuple is a key-value pair.

```
class LinearMap:

    def __init__(self):
        self.items = []

    def add(self, k, v):
        self.items.append((k, v))

    def get(self, k):
        for key, val in self.items:
            if key == k:
                return val
```
