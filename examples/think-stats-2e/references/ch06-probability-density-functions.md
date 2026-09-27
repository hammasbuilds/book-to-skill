# Chapter 6: Probability density functions

Source pages 95-110 of the PDF.

## When to use

Open this file for questions about: probability density, moment, sample skewness, cumulative, kernel, continuous, discrete, skews.

## Sections

The code for this chapter is in density.py. For information about downloading and working with this code, see Section 0.2.

### 6.1 PDFs

The derivative of a CDF is called a probability density function, or PDF. For example, the PDF of an exponential distribution is

### 6.2 Kernel density estimation

Kernel density estimation (KDE) is an algorithm that takes a sample and finds an appropriately smooth PDF that fits the data. You can read details at http://en.wikipedia.org/wiki/Kernel_density_estimation.

### 6.3 The distribution framework

At this point we have seen PMFs, CDFs and PDFs; let’s take a minute to review. Figure 6.2 shows how these functions relate to each other.

### 6.4 Hist implementation

At this point you should know how to use the basic types provided by thinkstats2: Hist, Pmf, Cdf, and Pdf. The next few sections provide details about how they are implemented.

### 6.5 Pmf implementation

Pmf and Hist are almost the same thing, except that a Pmf maps values to floating-point probabilities, rather than integer frequencies. If the sum of the probabilities is 1, the Pmf is normalized.

### 6.6 Cdf implementation

A CDF maps from values to cumulative probabilities, so I could have implemented Cdf as a _DictWrapper. But the values in a CDF are ordered and the values in a _DictWrapper are not.

### 6.7 Moments

Any time you take a sample and reduce it to a single number, that number is a statistic. The statistics we have seen so far include mean, variance, median, and interquartile range.

### 6.8 Skewness

Skewness is a property that describes the shape of a distribution. If the distribution is symmetric around its central tendency, it is unskewed.

### 6.9 Exercises

A solution to this exercise is in chap06soln.py.

### 6.10 Glossary

• Probability density function (PDF): The derivative of a continuous CDF, a function that maps a value to its probability density.

## Key definitions

- The derivative of a CDF is called a probability density function, or PDF.
- The result is a gaussian_kde object that provides an evaluate method.
- sample is a list of 500 random heights. sample_pdf is a Pdf object that contains the estimated KDE of the sample.
- The definition of variance gives a hint about why these statistics are called moments.
- Skewness is a property that describes the shape of a distribution.
- g1 is the third standardized moment, which means that it has been normalized so it has no units.
- This statistic is robust, which means that it is less vulnerable to the effect of outliers.

## Worked examples

From *PDFs*: For example, thinkstats2 provides a class named NormalPdf that evaluates the normal density function.

```
class NormalPdf(Pdf):

    def __init__(self, mu=0, sigma=1, label=''):
        self.mu = mu
        self.sigma = sigma
        self.label = label

    def Density(self, xs):
        return scipy.stats.norm.pdf(xs, self.mu, self.sigma)

    def GetLinspace(self):
        low, high = self.mu-3*self.sigma, self.mu+3*self.sigma
```

From *Kernel density estimation*: Figure 6.1: A normal PDF that models adult female height in the U.S., and the kernel density estimate of a sample with n = 500.

```
class EstimatedPdf(Pdf):

    def __init__(self, sample):
        self.kde = scipy.stats.gaussian_kde(sample)

    def Density(self, xs):
        return self.kde.evaluate(xs)
```

From *Hist implementation*: For example:

```
# class _DictWrapper

    def Incr(self, x, term=1):
        self.d[x] = self.d.get(x, 0) + term

    def Mult(self, x, factor):
        self.d[x] = self.d.get(x, 0) * factor

    def Remove(self, x):
        del self.d[x]
```

From *Pmf implementation*: Pmf provides Normalize, which computes the sum of the probabilities and divides through by a factor:

```
# class Pmf

    def Normalize(self, fraction=1.0):
               total = self.Total()
               if total == 0.0:
                   raise ValueError('Total probability is zero.')

               factor = float(fraction) / total
               for x in self.d:
                   self.d[x] *= factor

               return total
```
