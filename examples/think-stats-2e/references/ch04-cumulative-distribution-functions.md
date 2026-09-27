# Chapter 4: Cumulative distribution functions

Source pages 65-76 of the PDF.

## When to use

Open this file for questions about: percentile rank, cumulative distribution, percentilerank, given value, function cdf, field, birth weights, chosen.

## Sections

The code for this chapter is in cumulative.py. For information about downloading and working with this code, see Section 0.2.

### 4.1 The limits of PMFs

PMFs work well if the number of values is small. But as the number of values increases, the probability associated with each value gets smaller and the effect of random noise increases.

### 4.2 Percentiles

If you have taken a standardized test, you probably got your results in the form of a raw score and a percentile rank. In this context, the percentile rank is the fraction of people who scored lower than you (or the same).

### 4.3 CDFs

Now that we understand percentiles and percentile ranks, we are ready to tackle the cumulative distribution function (CDF). The CDF is the function that maps from a value to its percentile rank.

### 4.4 Representing CDFs

thinkstats2 provides a class named Cdf that represents CDFs. The fundamental methods Cdf provides are:

### 4.5 Comparing CDFs

CDFs are especially useful for comparing distributions. For example, here is the code that plots the CDF of birth weight for first babies and others.

### 4.6 Percentile-based statistics

Once you have computed a CDF, it is easy to compute percentiles and percentile ranks. The Cdf class provides these two methods:

### 4.7 Random numbers

Suppose we choose a random sample from the population of live births and look up the percentile rank of their birth weights. Now suppose we compute the CDF of the percentile ranks.

### 4.8 Comparing percentile ranks

Percentile ranks are useful for comparing measurements across different groups. For example, people who compete in foot races are usually grouped by age and gender.

### 4.9 Exercises

For the following exercises, you can start with chap04ex.ipynb. My solution is in chap04soln.ipynb.

### 4.10 Glossary

• percentile rank: The percentage of values in a distribution that are less than or equal to a given value.

## Key definitions

- Statistics like these that represent equally-spaced points in a CDF are called quantiles.
- The CDF is approximately a straight line, which means that the distribution is uniform.
- • replacement: A property of a sampling process. “With replacement” means that the same value can be chosen more than once; “without replacement” means that once a value is chosen, it is removed from the population.

## Worked examples

From *Percentiles*: Here’s how you could compute the percentile rank of a value, your_score, relative to the values in the sequence scores:

```
def PercentileRank(scores, your_score):
    count = 0
    for score in scores:
        if score <= your_score:
            count += 1

    percentile_rank = 100.0 * count / len(scores)
    return percentile_rank
```

From *CDFs*: Here’s what that looks like as a function that takes a sequence, sample, and a value, x:

```
def EvalCdf(sample, x):
    count = 0.0
    for value in sample:
        if value <= x:
            count += 1

    prob = count / len(sample)
    return prob
```

From *Representing CDFs*: The following code makes a Cdf for the distribution of pregnancy lengths in the NSFG:

```
live, firsts, others = first.MakeFrames()
cdf = thinkstats2.Cdf(live.prglngth, label='prglngth')
```

From *Comparing CDFs*: For example, here is the code that plots the CDF of birth weight for first babies and others.

```
first_cdf = thinkstats2.Cdf(firsts.totalwgt_lb, label='first')
other_cdf = thinkstats2.Cdf(others.totalwgt_lb, label='other')
```
