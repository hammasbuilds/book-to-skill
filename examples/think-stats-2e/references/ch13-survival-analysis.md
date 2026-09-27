# Chapter 13: Survival analysis

Source pages 215-235 of the PDF.

## When to use

Open this file for questions about: survival, curve, married, hazard function, lifetimes, marriage, cohort, remaining.

## Sections

Survival analysis is a way to describe how long things last. It is often used to study human lifetimes, but it also applies to “survival” of mechanical and electronic components, or more generally to intervals in time before an event.

### 13.1 Survival curves

The fundamental concept in survival analysis is the survival curve, S(t), which is a function that maps from a duration, t, to the probability of surviving longer than t. If you know the distribution of durations, or “lifetimes”, finding the survival curve is easy; it’s just the complement of the CDF:

### 13.2 Hazard function

From the survival curve we can derive the hazard function; for pregnancy lengths, the hazard function maps from a time, t, to the fraction of pregnancies that continue until t and then end at t. To be more precise:

### 13.3 Inferring survival curves

If someone gives you the CDF of lifetimes, it is easy to compute the survival and hazard functions. But in many real-world scenarios, we can’t measure the distribution of lifetimes directly.

### 13.4 Kaplan-Meier estimation

In this example it is not only desirable but necessary to include observations of unmarried women, which brings us to one of the central algorithms in survival analysis, Kaplan-Meier estimation.

### 13.5 The marriage curve

To test this function, we have to do some data cleaning and transformation.

### 13.6 Estimating the survival curve

Once we have the hazard function, we can estimate the survival curve. The chance of surviving past time t is the chance of surviving all times up through t, which is the cumulative product of the complementary hazard function:

### 13.7 Confidence intervals

Kaplan-Meier analysis yields a single estimate of the survival curve, but it is also important to quantify the uncertainty of the estimate. As usual, there are three possible sources of error: measurement error, sampling error, and modeling error.

### 13.8 Cohort effects

One of the challenges of survival analysis is that different parts of the estimated curve are based on different groups of respondents. The part of the curve at time t is based on respondents whose age was at least t when they were interviewed.

### 13.9 Extrapolation

The survival curve for the 70s cohort ends at about age 38; for the 80s cohort it ends at age 28, and for the 90s cohort we hardly have any data at all.

### 13.10 Expected remaining lifetime

Given a survival curve, we can compute the expected remaining lifetime as a function of current age. For example, given the survival curve of pregnancy length from Section 13.1, we can compute the expected time until delivery.

### 13.11 Exercises

My solution to this exercise is in chap13soln.py.

## Key definitions

- The fundamental concept in survival analysis is the survival curve, S(t), which is a function that maps from a duration, t, to the probability of surviving longer than t.
- In Python, a “property” is a method that can be invoked as if it were a variable.
- d can be a dictionary or any other type that can initialize a Series, including another Series. label is a string used to identify the HazardFunction when plotted.
- First, we precompute hist_complete, which is a Counter that maps from each age to the number of women married at that age, and hist_ongoing which maps from each age to the number of unmarried women interviewed at that age.
- In this context, “censored” means that the data are unavailable because of the data collection process.
- Groups like this, defined by date of birth or similar events, are called cohorts, and differences between the groups are called cohort effects.
- pmf is the Pmf of lifetimes extracted from the SurvivalFunction. d is a dictionary that contains the results, a map from current age, t, to expected remaining lifetime.
- Processes with this property are called memoryless because the past has no effect on the predictions.
- Mechanical components with this property are called NBUE for “new better than used in expectation,” meaning that a new part is expected to last longer.
- Components with this property are called UBNE for “used better than new in expectation.” That is, the older the part, the longer it is expected to last.
- sf2 is the survival curve for age at first marriage; func is a function that takes a Pmf and computes its median (50th percentile).

## Worked examples

From *Survival curves*: We can read this data and compute the CDF:

```
preg = nsfg.ReadFemPreg()
complete = preg.query('outcome in [1, 3, 4]').prglngth
cdf = thinkstats2.Cdf(complete, label='cdf')
```

From *Hazard function*: SurvivalFunction provides MakeHazard, which calculates the hazard function:

```
# class SurvivalFunction

    def MakeHazard(self, label=''):
        ss = self.ss
        lams = {}
        for i, t in enumerate(self.ts[:-1]):
            hazard = (ss[i] - ss[i+1]) / ss[i]
            lams[t] = hazard

        return HazardFunction(lams, label=label)
```

From *Kaplan-Meier estimation*: Here’s the code:

```
   def EstimateHazardFunction(complete, ongoing, label=''):

       hist_complete = Counter(complete)
       hist_ongoing = Counter(ongoing)

       ts = list(hist_complete | hist_ongoing)
       ts.sort()
at_risk = len(complete) + len(ongoing)

lams = pandas.Series(index=ts)
for t in ts:
    ended = hist_complete[t]
```

From *The marriage curve*: First, we read the respondent file and replace invalid values of cmmarrhx:

```
resp = chap01soln.ReadFemResp()
resp['cmmarrhx'] = resp.cmmarrhx.replace([9997, 9998, 9999], np.nan)
```
