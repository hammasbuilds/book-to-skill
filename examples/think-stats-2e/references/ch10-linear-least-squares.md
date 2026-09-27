# Chapter 10: Linear least squares

Source pages 157-171 of the PDF.

## When to use

Open this file for questions about: slope, residuals, inter, least squares, sampling distribution, null hypothesis, fitted line, linear.

## Sections

The code for this chapter is in linear.py. For information about downloading and working with this code, see Section 0.2.

### 10.1 Least squares fit

Correlation coefficients measure the strength and sign of a relationship, but not the slope. There are several ways to estimate the slope; the most common is a linear least squares fit.

### 10.2 Implementation

thinkstats2 provides simple functions that demonstrate linear least squares:

### 10.3 Residuals

Another useful test is to plot the residuals. thinkstats2 provides a function that computes residuals:

### 10.4 Estimation

The parameters slope and inter are estimates based on a sample; like other estimates, they are vulnerable to sampling bias, measurement error, and sampling error. As discussed in Chapter 8, sampling bias is caused by non-representative sampling, measurement error is caused by errors in collecting and recording data, and sampling error is the result of measuring a sample rather than the entire population.

### 10.5 Goodness of fit

There are several ways to measure the quality of a linear model, or goodness of fit. One of the simplest is the standard deviation of the residuals.

### 10.6 Testing a linear model

The effect of mother’s age on birth weight is small, and has little predictive power. So is it possible that the apparent relationship is due to chance?

### 10.7 Weighted resampling

So far we have treated the NSFG data as if it were a representative sample, but as I mentioned in Section 1.2, it is not. The survey deliberately oversamples several groups in order to improve the chance of getting statistically significant results; that is, in order to improve the power of tests involving these groups.

### 10.8 Exercises

A solution to this exercise is in chap10soln.ipynb

### 10.9 Glossary

• linear fit: a line intended to model the relationship between variables.

## Key definitions

- Nevertheless, the linear fit is a simple model that is probably good enough for some purposes.
- 2 For birth weight and mother’s age, R is 0.0047, which means that mother’s age predicts about half of 1% of variance in birth weight.
- This survey design is useful for many purposes, but it means that we cannot use the sample to estimate values for the general population without accounting for the sampling process.
- This value is called a sampling weight, or just “weight.” As an example, if you survey 100,000 people in a country of 300 million, each respondent represents 3,000 people.
- indices is a sequence of row indices; sample is a DataFrame that contains the selected rows.

## Worked examples

From *Implementation*: thinkstats2 provides simple functions that demonstrate linear least squares:

```
def LeastSquares(xs, ys):
    meanx, varx = MeanVar(xs)
    meany = Mean(ys)

    slope = Cov(xs, ys, meanx, meany) / varx
    inter = meany - slope * meanx

    return inter, slope
```

From *Residuals*: Another useful test is to plot the residuals. thinkstats2 provides a function that computes residuals:

```
def Residuals(xs, ys, inter, slope):
    xs = np.asarray(xs)
    ys = np.asarray(ys)
    res = ys - (inter + slope * xs)
    return res
```

From *Estimation*: I simulate the experiments by resampling the data; that is, I treat the observed pregnancies as if they were the entire population and draw samples, with replacement, from the observed sample.

```
def SamplingDistributions(live, iters=101):
    t = []
    for _ in range(iters):
        sample = thinkstats2.ResampleRows(live)
        ages = sample.agepreg
        weights = sample.totalwgt_lb
        estimates = thinkstats2.LeastSquares(ages, weights)
        t.append(estimates)

    inters, slopes = zip(*t)
    return inters, slopes
```

From *Goodness of fit*: Another way to measure goodness of fit is the coefficient of determina- 2 tion, usually denoted R and called “R-squared”:

```
def CoefDetermination(ys, res):
    return 1 - Var(res) / Var(ys)
```
