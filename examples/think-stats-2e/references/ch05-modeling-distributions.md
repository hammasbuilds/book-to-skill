# Chapter 5: Modeling distributions

Source pages 77-93 of the PDF.

## When to use

Open this file for questions about: pareto, scale, analytic, lognormal, normal probability, exponential distribution, model, empirical.

## Sections

The distributions we have used so far are called empirical distributions because they are based on empirical observations, which are necessarily finite samples.

### 5.1 The exponential distribution

I’ll start with the exponential distribution because it is relatively simple. The CDF of the exponential distribution is

### 5.2 The normal distribution

The normal distribution, also called Gaussian, is commonly used because it describes many phenomena, at least approximately. It turns out that there is a good reason for its ubiquity, which we will get to in Section 14.4.

### 5.3 Normal probability plot

For the exponential distribution, and a few others, there are simple transformations we can use to test whether an analytic distribution is a good model for a dataset.

### 5.4 The lognormal distribution

If the logarithms of a set of values have a normal distribution, the values have a lognormal distribution. The CDF of the lognormal distribution is the same as the CDF of the normal distribution, with log x substituted for x.

### 5.5 The Pareto distribution

The Pareto distribution is named after the economist Vilfredo Pareto, who used it to describe the distribution of wealth (see http://wikipedia. org/wiki/Pareto_distribution). Since then, it has been used to describe phenomena in the natural and social sciences including sizes of cities and towns, sand particles and meteorites, forest fires and earthquakes.

### 5.6 Generating random numbers

Analytic CDFs can be used to generate random numbers with a given distribution function, p = CDF(x). If there is an efficient way to compute the inverse CDF, we can generate random values with the appropriate distribution by choosing p from a uniform distribution between 0 and 1, then choosing x = ICDF (p).

### 5.7 Why model?

At the beginning of this chapter, I said that many real world phenomena can be modeled with analytic distributions. “So,” you might ask, “what?”

### 5.8 Exercises

For the following exercises, you can start with chap05ex.ipynb. My solution is in chap05soln.ipynb.

## Key definitions

- The distributions we have used so far are called empirical distributions because they are based on empirical observations, which are necessarily finite samples.
- In this context, a model is a simplification that leaves out unneeded details.
- The normal distribution with µ = 0 and σ = 1 is called the standard normal distribution.
- There is a simple visual test that indicates whether an empirical distribution fits a Pareto distribution: on a log-log scale, the CCDF looks like a straight line.
- cities, but it is a better fit for that part of the distribution.

## Worked examples

From *The exponential distribution*: The time of birth for all 44 babies was reported in the local paper; the complete dataset is in a file called babyboom.dat, in the ThinkStats2 repository.

```
df = ReadBabyBoom()
diffs = df.minutes.diff()
cdf = thinkstats2.Cdf(diffs, label='actual')

thinkplot.Cdf(cdf)
thinkplot.Show(xlabel='minutes', ylabel='CDF')
```

From *The normal distribution*: One of them is provided by SciPy: scipy.stats.norm is an object that represents a normal distribution; it provides a method, cdf, that evaluates the standard normal CDF:

```
>>> import scipy.stats
>>> scipy.stats.norm.cdf(0)
0.5
```

From *Normal probability plot*: It plots a gray line that represents the model and a blue line that represents the data.

```
def MakeNormalPlot(weights):
    mean = weights.mean()
    std = weights.std()

    xs = [-4, 4]
    fxs, fys = thinkstats2.FitLine(xs, inter=mean, slope=std)
```

From *Generating random numbers*: Figure 5.11: CDF of city and town populations on a log-x scale (left), and normal probability plot of log-transformed populations (right).

```
p = random.random()
x = -math.log(1-p) / lam
return x
```
