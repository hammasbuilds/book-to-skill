# Chapter 9: Case study: word play

Source pages 105-110 of the PDF.

## When to use

Open this file for questions about: solved problem, return false, forbidden, required letters, palindromic, words, file object, cartalk.

## Sections

This chapter presents the second case study, which involves solving word puzzles by searching for words that have certain properties. For example, we’ll find the longest palindromes in English and search for words whose letters appear in alphabetical order.

### 9.1 Reading word lists

For the exercises in this chapter we need a list of English words. There are lots of word lists available on the Web, but the one most suitable for our purpose is one of the word lists collected and contributed to the public domain by Grady Ward as part of the Moby lexicon project (see http://wikipedia.org/wiki/Moby_Project).

### 9.2 Exercises

There are solutions to these exercises in the next section. You should at least attempt each one before you read the solutions.

### 9.3 Search

All of the exercises in the previous section have something in common; they can be solved with the search pattern we saw in Section 8.6. The simplest example is:

### 9.4 Looping with indices

I wrote the functions in the previous section with for loops because I only needed the characters in the strings; I didn’t have to do anything with the indices.

### 9.5 Debugging

Testing programs is hard. The functions in this chapter are relatively easy to test because you can check the results by hand.

### 9.7 Exercises

Exercise 9.7. This question is based on a Puzzler that was broadcast on the radio program Car Talk (http: // www. cartalk. com/ content/ puzzlers):

## Key definitions

- This is an example of a program development plan called reduction to a previously solved problem, which means that you recognize the problem you are working on as an instance of a solved problem and apply an existing solution.
- But there is a word that has three consecutive pairs of letters and to the best of my knowledge this may be the only word.

## Worked examples

From *Reading word lists*: The file object provides several methods for reading, including readline, which reads characters from the file until it gets to a newline and returns the result as a string:

```
>>> fin.readline()
'aa\n'
```

From *Search*: The simplest example is:

```
def has_no_e(word):
    for letter in word:
        if letter == 'e':
            return False
    return True
```

From *Looping with indices*: For is_abecedarian we have to compare adjacent letters, which is a little tricky with a for loop:

```
def is_abecedarian(word):
    previous = word[0]
    for c in word:
        if c < previous:
            return False
        previous = c
    return True
```
