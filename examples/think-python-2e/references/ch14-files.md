# Chapter 14: Files

Source pages 159-168 of the PDF.

## When to use

Open this file for questions about: current directory, database, path, files, format, permanent storage, pickle, imported.

## Sections

This chapter introduces the idea of “persistent” programs that keep data in permanent storage, and shows how to use different kinds of permanent storage, like files and databases.

### 14.1 Persistence

Most of the programs we have seen so far are transient in the sense that they run for a short time and produce some output, but when they end, their data disappears. If you run the program again, it starts with a clean slate.

### 14.2 Reading and writing

A text file is a sequence of characters stored on a permanent medium like a hard drive, flash memory, or CD-ROM. We saw how to open and read a file in Section 9.1.

### 14.3 Format operator

The argument of write has to be a string, so if we want to put other values in a file, we have to convert them to strings. The easiest way to do that is with str:

### 14.4 Filenames and paths

Files are organized into directories (also called “folders”). Every running program has a “current directory”, which is the default directory for most operations.

### 14.5 Catching exceptions

A lot of things can go wrong when you try to read and write files. If you try to open a file that doesn’t exist, you get an FileNotFoundError:

### 14.6 Databases

A database is a file that is organized for storing data. Many databases are organized like a dictionary in the sense that they map from keys to values.

### 14.7 Pickling

A limitation of dbm is that the keys and values have to be strings or bytes. If you try to use any other type, you get an error.

### 14.8 Pipes

Most operating systems provide a command-line interface, also known as a shell. Shells usually provide commands to navigate the file system and launch applications.

### 14.9 Writing modules

Any file that contains Python code can be imported as a module. For example, suppose you have a file named wc.py with the following code:

### 14.10 Debugging

When you are reading and writing files, you might run into problems with whitespace. These errors can be hard to debug because spaces, tabs and newlines are normally invisible:

### 14.11 Glossary

persistent: Pertaining to a program that runs indefinitely and keeps at least some of its data in permanent storage.

### 14.12 Exercises

Exercise 14.1. Write a function called sed that takes as arguments a pattern string, a replacement string, and two filenames; it should read the first file and write the contents into the second file (creating it if necessary).

## Key definitions

- For example, the format sequence '%d' means that the second operand should be formatted as a decimal integer:
- The os module provides functions for working with files and directories (“os” stands for “operating system”). os.getcwd returns the name of the current directory:
- cwd stands for “current working directory”.
- A string like '/home/dinsdale' that identifies a file or directory is called a path.
- If the current directory is /home/dinsdale, the filename memo.txt would refer to /home/dinsdale/memo.txt.
- A path that begins with / does not depend on the current directory; it is called an absolute path.
- Handling an exception with a try statement is called catching an exception.
- A database is a file that is organized for storing data.
- The mode 'c' means that the database should be created if it doesn’t already exist.
- The result is a database object that can be used (for most operations) like a dictionary.
- pickle.dumps takes an object as a parameter and returns a string representation (dumps is short for “dump string”):
- The argument is a string that contains a shell command.

## Worked examples

From *Reading and writing*: The write method puts data into the file.

```
>>> line1 = "This here's the wattle,\n"
>>> fout.write(line1)
24
```

From *Format operator*: The easiest way to do that is with str:

```
>>> x = 52
>>> fout.write(str(x))
```

From *Filenames and paths*: The os module provides functions for working with files and directories (“os” stands for “operating system”). os.getcwd returns the name of the current directory:

```
>>> import os
>>> cwd = os.getcwd()
>>> cwd
'/home/dinsdale'
```

From *Catching exceptions*: If you try to open a file that doesn’t exist, you get an FileNotFoundError:

```
>>> fin = open('bad_file')
FileNotFoundError: [Errno 2] No such file or directory: 'bad_file'
```
