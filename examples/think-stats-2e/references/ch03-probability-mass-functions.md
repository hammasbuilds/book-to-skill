# Chapter 3: Probability mass functions

Source pages 51-63 of the PDF.

## When to use

Open this file for questions about: class size, number students, runners, children, speed, pmfs, relay, figures.

## Sections

The code for this chapter is in probability.py. For information about downloading and working with this code, see Section 0.2.

### 3.1 Pmfs

Another way to represent a distribution is a probability mass function (PMF), which maps from each value to its probability. A probability is a frequency expressed as a fraction of the sample size, n.

### 3.2 Plotting PMFs

thinkplot provides two ways to plot Pmfs:

### 3.3 Other visualizations

Histograms and PMFs are useful while you are exploring data and trying to identify patterns and relationships. Once you have an idea what is going on, a good next step is to design a visualization that makes the patterns you have identified as clear as possible.

### 3.4 The class size paradox

Before we go on, I want to demonstrate one kind of computation you can do with Pmf objects; I call this example the “class size paradox.”

### 3.5 DataFrame indexing

In Section 1.4 we read a pandas DataFrame and used it to select and modify data columns. Now let’s look at row selection.

### 3.6 Exercises

Solutions to these exercises are in chap03soln.ipynb and chap03soln.py

### 3.7 Glossary

• Probability mass function (PMF): a representation of a distribution as a function that maps from values to probabilities.

## Key definitions

- To get from frequencies to probabilities, we divide through by n, which is called normalization.
- The result is a new Pmf that represents the biased distribution.
- The set of row names is called the index; the row names themselves are called labels.
- • index: In a pandas DataFrame, the index is a special column that contains the row labels.

## Worked examples

From *Pmfs*: Given a Hist, we can make a dictionary that maps from each value to its probability:

```
n = hist.Total()
d = {}
for x, freq in hist.Items():
    d[x] = freq / n
```

From *Plotting PMFs*: Figure 3.1: PMF of pregnancy lengths for first babies and others, using bar graphs and step functions.

```
thinkplot.PrePlot(2, cols=2)
thinkplot.Hist(first_pmf, align='right', width=width)
thinkplot.Hist(other_pmf, align='left', width=width)
thinkplot.Config(xlabel='weeks',
                 ylabel='probability',
                 axis=[27, 46, 0, 0.6])

thinkplot.PrePlot(2)
thinkplot.SubPlot(2)
thinkplot.Pmfs([first_pmf, other_pmf])
thinkplot.Show(xlabel='weeks',
               axis=[27, 46, 0, 0.6])
```

From *Other visualizations*: So it makes sense to zoom in on that part of the graph, and to transform the data to emphasize differences:

```
weeks = range(35, 46)
diffs = []
for week in weeks:
    p1 = first_pmf.Prob(week)
    p2 = other_pmf.Prob(week)
    diff = 100 * (p1 - p2)
    diffs.append(diff)

thinkplot.Bar(weeks, diffs)
```

From *The class size paradox*: Suppose that a college offers 65 classes in a given semester, with the following distribution of sizes:

```
 size count
 5- 9 8
10-14 8
15-19 14
20-24 4
25-29 6
30-34 12
35-39 8
40-44 3
45-49 2
```
