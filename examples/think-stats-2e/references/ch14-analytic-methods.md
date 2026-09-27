# Chapter 14: Analytic methods

Source pages 237-254 of the PDF.

## When to use

Open this file for questions about: sampling distribution, sums, limit theorem, normal, analytic, exponential values, computational, chi-squared.

## Sections

This book has focused on computational methods like simulation and resampling, but some of the problems we solved have analytic solutions that can be much faster.

### 14.1 Normal distributions

As a motivating example, let’s review the problem from Section 8.3:

### 14.2 Sampling distributions

Now we have everything we need to compute the sampling distribution of ¯ x. Remember that we compute ¯ x by weighing n gorillas, adding up the total weight, and dividing by n.

### 14.3 Representing normal distributions

To make these calculations easier, I have defined a class called Normal that represents a normal distribution and encodes the equations in the previous sections. Here’s what it looks like:

### 14.4 Central limit theorem

As we saw in the previous sections, if we add values drawn from normal distributions, the distribution of the sum is normal. Most other distributions don’t have this property; if we add values drawn from other distributions, the sum does not generally have an analytic distribution.

### 14.5 Testing the CLT

To see how the Central Limit Theorem works, and when it doesn’t, let’s try some experiments. First, we’ll try an exponential distribution:

### 14.6 Applying the CLT

To see why the Central Limit Theorem is useful, let’s get back to the example in Section 9.3: testing the apparent difference in mean pregnancy length for first babies and others. As we’ve seen, the apparent difference is about 0.078 weeks:

### 14.7 Correlation test

In Section 9.5 we used a permutation test for the correlation between birth weight and mother’s age, and found that it is statistically significant, with p-value less than 0.001.

### 14.8 Chi-squared test

In Section 9.7 we used the chi-squared statistic to test whether a die is crooked. The chi-squared statistic measures the total normalized deviation from the expected values in a table:

### 14.9 Discussion

This book focuses on computational methods like resampling and permutation. These methods have several advantages over analysis:

### 14.10 Exercises

A solution to these exercises is in chap14soln.py

## Key definitions

- where the symbol ∼ means “is distributed” and the script letter N stands for “normal.”
- Each time we call np.random.exponential, we get a sequence of n exponential values and compute its sum. sample is a list of these sums, with length iters.
- normal is a list of correlated normal values. uniform is a sequence of uniform values between 0 and 1. expo is a correlated sequence of exponential values. ppf stands for “percent point function,” which is another name for the inverse CDF.
- Which means that the p-value for a one-sided test is 0.084.
- The parameter of the t-distribution, df, stands for “degrees of freedom.” I won’t explain that term, but you can read about it at http://en.wikipedia.org/wiki/Degrees_of_freedom_ (statistics).
- One reason the chi-squared statistic is widely used is that its sampling distri- 1 bution under the null hypothesis is analytic; by a remarkable coincidence, it is called the chi-squared distribution.

## Worked examples

From *Sampling distributions*: There is no closed form for the CDF of the normal distribution or its inverse, but there are fast numerical methods and they are implemented in SciPy, as we saw in Section 5.2. thinkstats2 provides a wrapper function that makes the SciPy function a little easier to use:

```
def EvalNormalCdfInverse(p, mu=0, sigma=1):
    return scipy.stats.norm.ppf(p, loc=mu, scale=sigma)
```

From *Representing normal distributions*: Here’s what it looks like:

```
class Normal(object):

    def __init__(self, mu, sigma2):
        self.mu = mu
        self.sigma2 = sigma2

    def __str__(self):
        return 'N(%g, %g)' % (self.mu, self.sigma2)
```

From *Testing the CLT*: First, we’ll try an exponential distribution:

```
def MakeExpoSamples(beta=2.0, iters=1000):
    samples = []
    for n in [1, 10, 100]:
        sample = [np.sum(np.random.exponential(beta, n))
                  for _ in range(iters)]
        samples.append((n, sample))
    return samples
```

From *Applying the CLT*: As we’ve seen, the apparent difference is about 0.078 weeks:

```
>>> live, firsts, others = first.MakeFrames()
>>> delta = firsts.prglngth.mean() - others.prglngth.mean()
0.078
```
