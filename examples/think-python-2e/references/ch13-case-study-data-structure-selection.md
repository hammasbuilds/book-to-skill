# Chapter 13: Case study: data structure selection

Source pages 147-157 of the PDF.

## When to use

Open this file for questions about: random, prefix, histogram, emma, suffixes, markov analysis, frequency, words.

## Sections

At this point you have learned about Python’s core data structures, and you have seen some of the algorithms that use them. If you would like to know more about algorithms, this might be a good time to read Chapter B.

### 13.1 Word frequency analysis

As usual, you should at least attempt the exercises before you read my solutions.

### 13.2 Random numbers

Given the same inputs, most computer programs generate the same outputs every time, so they are said to be deterministic. Determinism is usually a good thing, since we expect the same calculation to yield the same result.

### 13.3 Word histogram

You should attempt the previous exercises before you go on. You can download my solution from https://thinkpython.com/code/analyze_book1.py.

### 13.4 Most common words

To find the most common words, we can make a list of tuples, where each tuple contains a word and its frequency, and sort it.

### 13.5 Optional parameters

We have seen built-in functions and methods that take optional arguments. It is possible to write programmer-defined functions with optional arguments, too.

### 13.6 Dictionary subtraction

Finding the words from the book that are not in the word list from words.txt is a problem you might recognize as set subtraction; that is, we want to find all the words from one set (the words in the book) that are not in the other (the words in the list).

### 13.7 Random words

To choose a random word from the histogram, the simplest algorithm is to build a list with multiple copies of each word, according to the observed frequency, and then choose from the list:

### 13.8 Markov analysis

If you choose words from the book at random, you can get a sense of the vocabulary, but you probably won’t get a sentence:

### 13.9 Data structures

Using Markov analysis to generate random text is fun, but there is also a point to this exercise: data structure selection. In your solution to the previous exercises, you had to choose:

### 13.10 Debugging

When you are debugging a program, and especially if you are working on a hard bug, there are five things to try:

### 13.12 Exercises

Exercise 13.9. The “rank” of a word is its position in a list of words sorted by frequency: the most common word has rank 1, the second most common has rank 2, etc.

## Key definitions

- Here is a program that reads a file and builds a histogram of the words in the file:
- (It is a shorthand to say that strings are “converted”; remember that strings are immutable, so methods like strip and lower return new strings.)
- Here is a loop that prints the ten most common words:
- For example, here is a function that prints the most common words in a histogram

## Worked examples

From *Word frequency analysis*: Let’s see if we can make Python swear:

```
>>> import string
>>> string.punctuation
'!"#$%&\'()*+,-./:;<=>?@[\\]^_/grave.ts1{|}~'
```

From *Random numbers*: To see a sample, run this loop:

```
import random

for i in range(10):
    x = random.random()
    print(x)
```

From *Word histogram*: Here is a program that reads a file and builds a histogram of the words in the file:

```
import string

def process_file(filename):
    hist = dict()
    fp = open(filename)
    for line in fp:
        process_line(line, hist)
    return hist

def process_line(line, hist):
    line = line.replace('-', ' ')

```

From *Most common words*: The following function takes a histogram and returns a list of word-frequency tuples:

```
def most_common(hist):
    t = []
    for key, value in hist.items():
        t.append((value, key))

    t.sort(reverse=True)
    return t
```
