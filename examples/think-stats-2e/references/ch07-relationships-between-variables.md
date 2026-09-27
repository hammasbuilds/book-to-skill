# Chapter 7: Relationships between variables

Source pages 111-124 of the PDF.

## When to use

Open this file for questions about: correlation, rank, covariance, scatter, relationship, controlled, spearman, pearson.

## Sections

So far we have only looked at one variable at a time. In this chapter we look at relationships between variables.

### 7.1 Scatter plots

The simplest way to check for a relationship between two variables is a scatter plot, but making a good scatter plot is not always easy. As an example, I’ll plot weight versus height for the respondents in the BRFSS (see Section 5.4).

### 7.2 Characterizing relationships

Scatter plots provide a general impression of the relationship between variables, but there are other visualizations that provide more insight into the nature of the relationship. One option is to bin one variable and plot percentiles of the other.

### 7.3 Correlation

A correlation is a statistic intended to quantify the strength of the relationship between two variables.

### 7.4 Covariance

Covariance is a measure of the tendency of two variables to vary together. If we have two series, X and Y, their deviations from the mean are

### 7.5 Pearson’s correlation

Covariance is useful in some computations, but it is seldom reported as a summary statistic because it is hard to interpret. Among other problems, its units are the product of the units of X and Y.

### 7.6 Nonlinear relationships

If Pearson’s correlation is near 0, it is tempting to conclude that there is no relationship between the variables, but that conclusion is not valid. Pearson’s correlation only measures linear relationships.

### 7.7 Spearman’s rank correlation

Pearson’s correlation works well if the relationship between variables is linear and if the variables are roughly normal. But it is not robust in the presence of outliers.

### 7.8 Correlation and causation

If variables A and B are correlated, there are three possible explanations: A causes B, or B causes A, or some other set of factors causes both A and B. These explanations are called “causal relationships”.

### 7.9 Exercises

A solution to this exercise is in chap07soln.py.

### 7.10 Glossary

• scatter plot: A visualization of the relationship between two variables, showing one point for each row of data.

## Key definitions

- groupby is a DataFrame method that returns a GroupBy object; used in a for loop, groups iterates the names of the groups and the DataFrames that represent them.
- This value is called Pearson’s correlation after Karl Pearson, an influential early statistician.
- If ρ is positive, we say that the correlation is positive, which means that when one variable is high, the other tends to be high.
- If ρ is 1 or -1, the variables are perfectly correlated, which means that if you know one, you can make a perfect prediction about the other.
- These explanations are called “causal relationships”.

## Worked examples

From *Scatter plots*: Here’s the code that reads the data file and extracts height and weight:

```
df = brfss.ReadBrfss(nrows=None)
sample = thinkstats2.SampleRows(df, 5000)
heights, weights = sample.htm3, sample.wtkg2
```

From *Characterizing relationships*: NumPy and pandas provide functions for binning data:

```
df = df.dropna(subset=['htm3', 'wtkg2'])
bins = np.arange(135, 210, 5)
indices = np.digitize(df.htm3, bins)
groups = df.groupby(indices)
```

From *Covariance*: So the covariance is maximized if the two vectors are identical, 0 if they are orthogonal, and negative if they point in opposite directions. thinkstats2 uses np.dot to implement Cov efficiently:

```
def Cov(xs, ys, meanx=None, meany=None):
    xs = np.asarray(xs)
    ys = np.asarray(ys)

    if meanx is None:
        meanx = np.mean(xs)
    if meany is None:
        meany = np.mean(ys)

    cov = np.dot(xs-meanx, ys-meany) / len(xs)
    return cov
```

From *Pearson’s correlation*: Here is the implementation in thinkstats2:

```
def Corr(xs, ys):
    xs = np.asarray(xs)
    ys = np.asarray(ys)

    meanx, varx = MeanVar(xs)
    meany, vary = MeanVar(ys)

    corr = Cov(xs, ys, meanx, meany) / math.sqrt(varx * vary)
    return corr
```
