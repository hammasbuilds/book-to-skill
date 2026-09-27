# Chapter 11: Regression

Source pages 173-191 of the PDF.

## When to use

Open this file for questions about: logistic regression, explanatory, dependent variable, isfirst, model, odds, agepreg, race.

## Sections

The linear least squares fit in the previous chapter is an example of regression, which is the more general problem of fitting any kind of model to any kind of data. This use of the term “regression” is a historical accident; it is only indirectly related to the original meaning of the word.

### 11.1 StatsModels

In the previous chapter I presented thinkstats2.LeastSquares, an implementation of simple linear regression intended to be easy to read. For multiple regression we’ll switch to StatsModels, a Python package that provides several forms of regression and other analyses.

### 11.2 Multiple regression

In Section 4.5 we saw that first babies tend to be lighter than others, and this effect is statistically significant. But it is a strange result because there is no obvious mechanism that would cause first babies to be lighter.

### 11.3 Nonlinear relationships

Remembering that the contribution of agepreg might be nonlinear, we might consider adding a variable to capture more of this relationship. One option is to create a column, agepreg2, that contains the squares of the ages:

### 11.4 Data mining

So far we have used regression models for explanation; for example, in the previous section we discovered that an apparent difference in birth weight 2 is actually due to a difference in mother’s age. But the R values of those models is very low, which means that they have little predictive power.

### 11.5 Prediction

The next step is to sort the results and select the variables that yield the 2 highest values of R.

### 11.6 Logistic regression

In the previous examples, some of the explanatory variables were numerical and some categorical (including boolean). But the dependent variable was always numerical.

### 11.7 Estimating parameters

Unlike linear regression, logistic regression does not have a closed form solution, so it is solved by guessing an initial solution and improving it iteratively.

### 11.8 Implementation

StatsModels provides an implementation of logistic regression called logit, named for the function that converts from probability to log odds. To demonstrate its use, I’ll look for variables that affect the sex ratio.

### 11.9 Accuracy

In the office pool scenario, we are most interested in the accuracy of the model: the number of successful predictions, compared with what we would expect by chance.

### 11.10 Exercises

My solution to these exercises is in chap11soln.ipynb.

## Key definitions

- This process is called ordinary least squares.
- The name ols stands for “ordinary least squares.”
- The results are also available as attributes. params is a Series that maps from variable names to their parameters, so we can get the intercept and slope like this:
- pvalues is a Series that maps from variable names to the associated p-values, so we can check whether the estimated slope is statistically significant:
- Because isfirst is a boolean, ols treats it as a categorical variable, which means that the values fall into categories, like True and False, and should not be treated as numbers.
- The slope and the intercept are statistically significant, which means that 2 they were unlikely to occur by chance, but the the R value for this model is small, which means that isfirst doesn’t account for a substantial part of the variation in birth weight.
- In the combined model, the parameter for isfirst is smaller by about half, which means that part of the apparent effect of isfirst is actually accounted for by agepreg.
- But the R values of those models is very low, which means that they have little predictive power.
- In this example some column names appear in both tables, so we have to provide rsuffix, which is a string that will be appended to the names of overlapping columns from the right table.
- The second approach, which this section demonstrates, is called data mining.
- If the dependent variable is boolean, the generalized model is called logistic regression.
- The result is a Logit object that represents the model.

## Worked examples

From *StatsModels*: As an example, I’ll run the model from the previous chapter with StatsModels:

```
import statsmodels.formula.api as smf

live, firsts, others = first.MakeFrames()
formula = 'totalwgt_lb ~ agepreg'
model = smf.ols(formula, data=live)
results = model.fit()
```

From *Multiple regression*: Running the linear model again, we get the change in birth weight as a function of age:

```
results = smf.ols('totalwgt_lb ~ agepreg', data=live).fit()
slope = results.params['agepreg']
```

From *Nonlinear relationships*: One option is to create a column, agepreg2, that contains the squares of the ages:

```
live['agepreg2'] = live.agepreg**2
formula = 'totalwgt_lb ~ isfirst + agepreg + agepreg2'
```

From *Data mining*: Join is implemented as a DataFrame method, so we can perform the operation like this:

```
live = live[live.prglngth>30]
resp = chap01soln.ReadFemResp()
resp.index = resp.caseid
join = live.join(resp, on='caseid', rsuffix='_r')
```
