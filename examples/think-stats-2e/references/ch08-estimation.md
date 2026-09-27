# Chapter 8: Estimation

Source pages 125-136 of the PDF.

## When to use

Open this file for questions about: estimator, estimation game, mean error, gorillas, sampling distribution, play, unbiased, rmse.

## Sections

The code for this chapter is in estimation.py. For information about downloading and working with this code, see Section 0.2.

### 8.1 The estimation game

Let’s play a game. I think of a distribution, and you have to guess what it is.

### 8.2 Guess the variance

I’m thinking of a distribution. It’s a normal distribution, and here’s a (familiar) sample:

### 8.3 Sampling distributions

Suppose you are a scientist studying gorillas in a wildlife preserve. You want to know the average weight of the adult female gorillas in the preserve.

### 8.4 Sampling bias

Suppose that instead of the weight of gorillas in a nature preserve, you want to know the average weight of women in the city where you live. It is unlikely that you would be allowed to choose a representative sample of women and weigh them.

### 8.5 Exponential distributions

Let’s play one more round of the estimation game. I’m thinking of a distribution.

### 8.6 Exercises

For the following exercises, you can find starter code in chap08ex.ipynb. Solutions are in chap08soln.py

## Key definitions

- This process is called estimation, and the statistic we used (the sample mean) is called an estimator.
- Here is a function that simulates the estimation game and computes the root mean squared error (RMSE), which is the square root of MSE:
- When I ran this code, the RMSE of the sample mean was 0.41, which means that if we use ¯x to estimate the mean of this distribution, based on a sample with n = 7, we should expect to be off by 0.41 on average.
- Because of this unfortunate property, it is called a biased estimator.
- The name “sample variance” can refer to either S or 2 2 S, and the symbol S is used for either or both.
- Here is a function that simulates the estimation game and tests the perfor- 2 2 mance of Sand S:
- Variation in the estimate caused by random selection is called sampling error.
- This distribution is called the sampling distribution of the estimator.
- The mean of the sampling distribution is pretty close to the hypothetical value of µ, which means that the experiment yields the right answer, on average.
- • A confidence interval (CI) is a range that includes a given fraction of the sampling distribution.
- This problem is called sampling bias because it is a property of the sampling process.

## Worked examples

From *The estimation game*: Here is a function that simulates the estimation game and computes the root mean squared error (RMSE), which is the square root of MSE:

```
def Estimate1(n=7, m=1000):
    mu = 0
    sigma = 1

    means = []
    medians = []
    for _ in range(m):
        xs = [random.gauss(mu, sigma) for i in range(n)]
        xbar = np.mean(xs)
        median = np.median(xs)
        means.append(xbar)
        medians.append(median)
```

From *Guess the variance*: n−1 def Estimate2(n=7, m=1000):

```
       mu = 0
       sigma = 1

       estimates1 = []
       estimates2 = []
       for _ in range(m):
           xs = [random.gauss(mu, sigma) for i in range(n)]
           biased = np.var(xs)
           unbiased = np.var(xs, ddof=1)
           estimates1.append(biased)
           estimates2.append(unbiased)
print('mean error biased', MeanError(estimates1, sigma**2))
```

From *Sampling distributions*: The following function answers that question:

```
def SimulateSample(mu=90, sigma=7.5, n=9, m=1000):
    means = []
    for j in range(m):
        xs = np.random.normal(mu, sigma, n)
        xbar = np.mean(xs)
        means.append(xbar)

    cdf = thinkstats2.Cdf(means)
    ci = cdf.Percentile(5), cdf.Percentile(95)
    stderr = RMSE(means, mu)
```

From *Exponential distributions*: To test the performance of these estimators, we can simulate the sampling process:

```
def Estimate3(n=7, m=1000):
    lam = 2

    means = []
    medians = []
    for _ in range(m):
        xs = np.random.exponential(1.0/lam, n)
        L = 1 / np.mean(xs)
        Lm = math.log(2) / thinkstats2.Median(xs)
        means.append(L)
        medians.append(Lm)

```
