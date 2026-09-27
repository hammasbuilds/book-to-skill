# Chapter 1: Exploratory data analysis

Source pages 21-36 of the PDF.

## When to use

Open this file for questions about: respondent, notebook, ipython, codebook, counts, file, indices, record.

## Sections

The thesis of this book is that data combined with practical methods can answer questions and guide decisions under uncertainty.

### 1.1 A statistical approach

To address the limitations of anecdotes, we will use the tools of statistics, which include:

### 1.2 The National Survey of Family Growth

Since 1973 the U.S. Centers for Disease Control and Prevention (CDC)

### 1.3 Importing the data

The code and data used in this book are available from https://github. com/AllenDowney/ThinkStats2. For information about downloading and working with this code, see Section 0.2.

### 1.4 DataFrames

The result of ReadFixedWidth is a DataFrame, which is the fundamental data structure provided by pandas, which is a Python data and statistics package we’ll use throughout this book. A DataFrame contains a row for each record, in this case one row per pregnancy, and a column for each variable.

### 1.5 Variables

We have already seen two variables in the NSFG dataset, caseid and pregordr, and we have seen that there are 244 variables in total. For the explorations in this book, I use the following variables:

### 1.6 Transformation

When you import data like this, you often have to check for errors, deal with special values, convert data into different formats, and perform calculations. These operations are called data cleaning.

### 1.7 Validation

When data is exported from one software environment and imported into another, errors might be introduced. And when you are getting familiar with a new dataset, you might interpret data incorrectly or introduce other misunderstandings.

### 1.8 Interpretation

To work with data effectively, you have to think on two levels at the same time: the level of statistics and the level of context.

### 1.9 Exercises

Exercise 1.1 In the repository you downloaded, you should find a file named chap01ex.ipynb, which is an IPython notebook. You can launch IPython notebook from the command line like this:

## Key definitions

- Reports like these are called anecdotal evidence because they are based on data that is unpublished and usually personal.
- The NSFG is a cross-sectional study, which means that it captures a snapshot of a group at a point in time.
- The NSFG has been conducted seven times; each deployment is called a cycle.
- The people who participate in a survey are called respondents.
- In general, cross-sectional studies are meant to be representative, which means that every member of the target population has an equal chance of participating.
- Each line in the file is a record that contains data about one pregnancy.
- The code you downloaded includes thinkstats2.py, which is a Python module that contains many classes and functions used in this book, including functions that read the Stata dictionary and the NSFG data file.
- If you read the codebook carefully, you will see that many of the variables are recodes, which means that they are not part of the raw data collected by the survey; they are calculated using the raw data.
- These operations are called data cleaning.
- d is a dictionary that maps from each case ID to a list of indices.
- The variable pregnum is a recode that indicates how many times each respondent has been pregnant.

## Worked examples

From *Importing the data*: For example, here are a few lines from 2002FemPreg.dct:

```
infile dictionary {
  _column(1) str12 caseid %12s "RESPONDENT ID NUMBER"
  _column(13) byte pregordr %2f "PREGNANCY ORDER (NUMBER)"
}
```

From *DataFrames*: If you print df you get a truncated view of the rows and columns, and the shape of the DataFrame, which is 13593 rows/records and 244 columns/variables.

```
>>> import nsfg
>>> df = nsfg.ReadFemPreg()
>>> df
...
[13593 rows x 244 columns]
```

From *Transformation*: nsfg.py includes CleanFemPreg, a function that cleans the variables I am planning to use.

```
def CleanFemPreg(df):
    df.agepreg /= 100.0

    na_vals = [97, 98, 99]
    df['birthwgt_lb'] = df.birthwgt_lb.replace(na_vals, np.nan)
    df['birthwgt_oz'] = df.birthwgt_oz.replace(na_vals, np.nan)

    df['totalwgt_lb'] = df.birthwgt_lb + df.birthwgt_oz / 16.0
```

From *Validation*: Here is the table for outcome, which encodes the outcome of each pregnancy:

```
value label Total
1 LIVE BIRTH 9148
2 INDUCED ABORTION 1862
3 STILLBIRTH 120
4 MISCARRIAGE 1921
5 ECTOPIC PREGNANCY 190
6 CURRENT PREGNANCY 352
```
