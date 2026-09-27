# Chapter 9: Hypothesis testing

Source pages 137-155 of the PDF.

## When to use

Open this file for questions about: null hypothesis, test statistic, runmodel, p-value, absolute, statistically significant, coin, chi-squared.

## Sections

The code for this chapter is in hypothesis.py. For information about downloading and working with this code, see Section 0.2.

### 9.1 Classical hypothesis testing

Exploring the data from the NSFG, we saw several “apparent effects,” including differences between first babies and others. So far we have taken these effects at face value; in this chapter, we put them to the test.

### 9.2 HypothesisTest

thinkstats2 provides HypothesisTest, a class that represents the structure of a classical hypothesis test. Here is the definition:

### 9.3 Testing a difference in means

One of the most common effects to test is a difference in mean between two groups. In the NSFG data, we saw that the mean pregnancy length for first babies is slightly longer, and the mean birth weight is slightly smaller.

### 9.4 Other test statistics

Choosing the best test statistic depends on what question you are trying to address. For example, if the relevant question is whether pregnancy lengths are different for first babies, then it makes sense to test the absolute difference in means, as we did in the previous section.

### 9.5 Testing a correlation

This framework can also test correlations. For example, in the NSFG data set, the correlation between birth weight and mother’s age is about 0.07.

### 9.6 Testing proportions

Suppose you run a casino and you suspect that a customer is using a crooked die; that is, one that has been modified to make one of the faces more likely than the others. You apprehend the alleged cheater and confiscate the die, but now you have to prove that it is crooked.

### 9.7 Chi-squared tests

In the previous section we used total deviation as the test statistic. But for testing proportions it is more common to use the chi-squared statistic:

### 9.8 First babies again

Earlier in this chapter we looked at pregnancy lengths for first babies and others, and concluded that the apparent differences in mean and standard deviation are not statistically significant. But in Section 3.3, we saw several apparent differences in the distribution of pregnancy length, especially in the range from 35 to 43 weeks.

### 9.9 Errors

In classical hypothesis testing, an effect is considered statistically significant if the p-value is below some threshold, commonly 5%. This procedure raises two questions:

### 9.10 Power

The false negative rate is harder to compute because it depends on the actual effect size, and normally we don’t know that. One option is to compute a rate conditioned on a hypothetical effect size.

### 9.11 Replication

The hypothesis testing process I demonstrated in this chapter is not, strictly speaking, good practice.

### 9.12 Exercises

A solution to these exercises is in chap09soln.py.

## Key definitions

- If the p-value is low, the effect is said to be statistically significant, which means that it is unlikely to have occurred by chance.
- The result is about 0.07, which means that if the coin is fair, we expect to see a difference as big as 30 about 7% of the time.
- The result is about 0.17, which means that we expect to see a difference as big as the observed effect about 17% of the time.
- This kind of test is called one-sided because it only counts one side of the distribution of differences.
- This example is a reminder that “statistically significant” does not always mean that an effect is important, or significant in practice.
- It only means that it is unlikely to have occurred by chance.
- The p-value for this data is 0.13, which means that if the die is fair we expect to see the observed total deviation, or more, about 13% of the time.
- The result is about 70%, which means that if the actual difference in mean pregnancy length is 0.078 weeks, we expect an experiment with this sample size to yield a negative test 70% of the time.
- This “correct positive rate” is called the power of the test, or sometimes “sensitivity”.

## Worked examples

From *HypothesisTest*: Here is the definition:

```
class HypothesisTest(object):

    def __init__(self, data):
        self.data = data
        self.MakeModel()
        self.actual = self.TestStatistic(data)

    def PValue(self, iters=1000):
        self.test_stats = [self.TestStatistic(self.RunModel())
                           for _ in range(iters)]

        count = sum(1 for x in self.test_stats if x >= self.actual)
```

From *Testing a difference in means*: One way to model the null hypothesis is by permutation; that is, we can take values for first babies and others and shuffle them, treating the two groups as one big group:

```
class DiffMeansPermute(thinkstats2.HypothesisTest):

    def TestStatistic(self, data):
        group1, group2 = data
        test_stat = abs(group1.mean() - group2.mean())
        return test_stat

    def MakeModel(self):
        group1, group2 = self.data
        self.n, self.m = len(group1), len(group2)
        self.pool = np.hstack((group1, group2))
           def RunModel(self):
```

From *Other test statistics*: If we had some reason to think that first babies are likely to be late, then we would not take the absolute value of the difference; instead we would use this test statistic:

```
class DiffMeansOneSided(DiffMeansPermute):

    def TestStatistic(self, data):
        group1, group2 = data
        test_stat = group1.mean() - group2.mean()
        return test_stat
```

From *Testing a correlation*: By shuffling the observed values, we can simulate a world where the distributions of age and birth weight are the same, but where the variables are unrelated:

```
class CorrelationPermute(thinkstats2.HypothesisTest):

    def TestStatistic(self, data):
        xs, ys = data
        test_stat = abs(thinkstats2.Corr(xs, ys))
        return test_stat

    def RunModel(self):
        xs, ys = self.data
        xs = np.random.permutation(xs)
        return xs, ys
```
