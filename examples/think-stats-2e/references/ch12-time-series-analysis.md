# Chapter 12: Time series analysis

Source pages 193-214 of the PDF.

## When to use

Open this file for questions about: time series, price, daily, quality, trend, medium, cannabis, moving.

## Sections

A time series is a sequence of measurements from a system that varies in time. One famous example is the “hockey stick graph” that shows global average temperature over time (see https://en.wikipedia.org/wiki/Hockey_ stick_graph).

### 12.1 Importing and cleaning

The data I downloaded from Mr. Jones’s site is in the repository for this book.

### 12.2 Plotting

The result from GroupByQualityAndDay is a map from each quality to a DataFrame of daily prices. Here’s the code I use to plot the three time series:

### 12.3 Linear regression

Although there are methods specific to time series analysis, for many problems a simple way to get started is by applying general-purpose tools like linear regression. The following function takes a DataFrame of daily prices and computes a least squares fit, returning the model and results objects from StatsModels:

### 12.4 Moving averages

Most time series analysis is based on the modeling assumption that the observed series is the sum of three components:

### 12.5 Missing values

Now that we have characterized the trend of the time series, the next step is to investigate seasonality, which is periodic behavior. Time series data based on human behavior often exhibits daily, weekly, monthly, or yearly cycles.

### 12.6 Serial correlation

As prices vary from day to day, you might expect to see patterns. If the price is high on Monday, you might expect it to be high for a few more days; and if it’s low, you might expect it to stay low.

### 12.7 Autocorrelation

If you think a series might have some serial correlation, but you don’t know which lags to test, you can test them all! The autocorrelation function is a function that maps from lag to the serial correlation with the given lag. “Autocorrelation” is another name for serial correlation, used more often when the lag is not 1.

### 12.8 Prediction

Time series analysis can be used to investigate, and sometimes explain, the behavior of systems that vary in time. It can also make predictions.

### 12.9 Further reading

Time series analysis is a big topic; this chapter has only scratched the surface. An important tool for working with time series data is autoregression, which I did not cover here, mostly because it turns out not to be useful for the example data I worked with.

### 12.10 Exercises

My solution to these exercises is in chap12soln.py.

## Key definitions

- groupby is a DataFrame method that returns a GroupBy object, groups; used in a for loop, it iterates the names of the groups and the DataFrames that represent them.
- The parameter, transactions, is a DataFrame that contains columns date and ppg.
- PrePlot with rows=3 means that we are planning to make three subplots laid out in three rows.
- 2 The R value for high quality cannabis is 0.44, which means that time as an explanatory variable accounts for 44% of the observed variability in price.
- A pattern like this is called serial correlation, because each value is correlated with the next one in the series.
- The autocorrelation function is a function that maps from lag to the serial correlation with the given lag. “Autocorrelation” is another name for serial correlation, used more often when the lag is not 1.
- You can see my code in timeseries.py; the function is called SimulateAutocorrelation.
- Here is a function that runs the simulations:
- GeneratePredictions takes the sequence of results from the previous step, as well as years, which is a sequence of floats that specifies the interval to generate predictions for, and add_resid, which indicates whether it should add resampled residuals to the straight-line prediction.

## Worked examples

From *Importing and cleaning*: In order to demonstrate these methods, I divide the dataset into groups by reported quality, and then transform each group into an equally spaced series by computing the mean daily price per gram.

```
def GroupByQualityAndDay(transactions):
    groups = transactions.groupby('quality')
    dailies = {}
    for name, group in groups:
        dailies[name] = GroupByDay(group)

    return dailies
```

From *Plotting*: Here’s the code I use to plot the three time series:

```
thinkplot.PrePlot(rows=3)
for i, (name, daily) in enumerate(dailies.items()):
    thinkplot.SubPlot(i+1)
    title = 'price per gram ($)' if i==0 else ''
    thinkplot.Config(ylim=[0, 20], title=title)
    thinkplot.Scatter(daily.index, daily.ppg, s=10, label=name)
    if i == 2:
        pyplot.xticks(rotation=30)
    else:
        thinkplot.Config(xticks=[])
```

From *Linear regression*: The following function takes a DataFrame of daily prices and computes a least squares fit, returning the model and results objects from StatsModels:

```
def RunLinearModel(daily):
    model = smf.ols('ppg ~ years', data=daily)
    results = model.fit()
    return model, results
```

From *Moving averages*: pandas provides rolling_mean, which takes a Series and a window size and returns a new Series.

```
>>> series = np.arange(10)
array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

>>> pandas.rolling_mean(series, 3)
array([ nan, nan, 1, 2, 3, 4, 5, 6, 7, 8])
```
