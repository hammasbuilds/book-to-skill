# Chapter 2: Distributions

Source pages 37-50 of the PDF.

## When to use

Open this file for questions about: figure histogram, pumpkin, summary statistic, hist, describe, part birth, modes, frequent.

## Sections

### 2.1 Histograms

One of the best ways to describe a variable is to report the values that appear in the dataset and how many times each value appears. This description is called the distribution of the variable.

### 2.2 Representing histograms

The Hist constructor can take a sequence, dictionary, pandas Series, or another Hist. You can instantiate a Hist object like this:

### 2.3 Plotting histograms

For this book I wrote a module called thinkplot.py that provides functions for plotting Hists and other objects defined in thinkstats2.py. It is based on pyplot, which is part of the matplotlib package.

### 2.4 NSFG variables

Now let’s get back to the data from the NSFG. The code in this chapter is in first.py.

### 2.5 Outliers

Looking at histograms, it is easy to identify the most common values and the shape of the distribution, but rare values are not always visible.

### 2.6 First babies

Now we can compare the distribution of pregnancy lengths for first babies and others. I divided the DataFrame of live births using birthord, and computed their histograms:

### 2.7 Summarizing distributions

A histogram is a complete description of the distribution of a sample; that is, given a histogram, we could reconstruct the values in the sample (although not their order).

### 2.8 Variance

If there is no single number that summarizes pumpkin weights, we can do a little better with two numbers: mean and variance.

### 2.9 Effect size

An effect size is a summary statistic intended to describe (wait for it) the size of an effect. For example, to describe the difference between two groups, one obvious choice is the difference in the means.

### 2.10 Reporting results

We have seen several ways to describe the difference in pregnancy length (if there is one) between first babies and others. How should we report these results?

### 2.11 Exercises

Exercise 2.1 Based on the results in this chapter, suppose you were asked to summarize what you learned about whether first babies arrive late.

## Key definitions

- This description is called the distribution of the variable.
- The most common representation of a distribution is a histogram, which is a graph that shows the frequency of each value.
- The result is a dictionary that maps from values to frequencies.
- The expression in brackets is a boolean Series that selects rows from the DataFrame and returns a new DataFrame.
- When the argument passed to Hist is a pandas Series, any nan values are dropped. label is a string that appears in the legend when the Hist is plotted.
- Statistics designed to answer these questions are called summary statistics.
- The term xi − x ¯ is called the “deviation from the mean,” so variance is the mean squared deviation.

## Worked examples

From *Histograms*: Given a sequence of values, t:

```
hist = {}
for x in t:
    hist[x] = hist.get(x, 0) + 1
```

From *Representing histograms*: You can instantiate a Hist object like this:

```
>>> import thinkstats2
>>> hist = thinkstats2.Hist([1, 2, 2, 3, 5])
>>> hist
Hist({1: 1, 2: 2, 3: 1, 5: 1})
```

From *Plotting histograms*: To plot hist with thinkplot, try this:

```
>>> import thinkplot
>>> thinkplot.Hist(hist)
>>> thinkplot.Show(xlabel='value', ylabel='frequency')
```

From *NSFG variables*: I’ll start by reading the data and selecting records for live births:

```
preg = nsfg.ReadFemPreg()
live = preg[preg.outcome == 1]
```
