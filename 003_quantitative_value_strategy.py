#!/usr/bin/env python
# coding: utf-8

# # Quantitative Value Strategy
# "Value investing" means investing in the stocks that are cheapest relative to common measures of business value (like earnings or assets).
# 
# For this project, we're going to build an investing strategy that selects the 50 stocks with the best value metrics. From there, we will calculate recommended trades for an equal-weight portfolio of these 50 stocks.
# 
# ## Library Imports
# The first thing we need to do is import the open-source software libraries that we'll be using in this tutorial.

# In[1]:


import numpy as np #The Numpy numerical computing library
import pandas as pd #The Pandas data science library
import requests #The requests library for HTTP requests in Python
import xlsxwriter #The XlsxWriter libarary for 
import math #The Python math module
from scipy import stats #The SciPy stats module


# ## Importing Our List of Stocks & API Token
# As before, we'll need to import our list of stocks and our API token before proceeding. Make sure the .csv file is still in your working directory and import it with the following command:

# In[2]:


stocks = pd.read_csv('sp_500_stocks.csv')
from secret import IEX_CLOUD_API_TOKEN


# ## Making Our First API Call
# It's now time to make the first version of our value screener!
# 
# We'll start by building a simple value screener that ranks securities based on a single metric (the price-to-earnings ratio).

# In[3]:


symbol = 'AAPL'
api_url = f'https://cloud.iexapis.com/stable/stock/{symbol}/quote?token={IEX_CLOUD_API_TOKEN}'
data = requests.get(api_url).json()
data


# 
# ## Parsing Our API Call
# This API call has the metric we need - the price-to-earnings ratio.
# 
# Here is an example of how to parse the metric from our API call:

# In[4]:


pe_ratio = data['peRatio']
pe_ratio


# 
# ## Executing A Batch API Call & Building Our DataFrame
# 
# Just like in our first project, it's now time to execute several batch API calls and add the information we need to our DataFrame.
# 
# We'll start by running the following code cell, which contains some code we already built last time that we can re-use for this project. More specifically, it contains a function called chunks that we can use to divide our list of securities into groups of 100.

# In[5]:


# Function sourced from 
# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]   
stocks = stocks[~stocks['Ticker'].isin(['DISCA', 'HFC','VIAC','WLTW'])]

symbol_groups = list(chunks(stocks['Ticker'], 100))
symbol_strings = []
for i in range(0, len(symbol_groups)):
    symbol_strings.append(','.join(symbol_groups[i]))
    #print(symbol_strings[i])

my_columns = ['Ticker', 'Price', 'Price-to-Earnings Ratio', 'Number of Shares to Buy']


# Now we need to create a blank DataFrame and add our data to the data frame one-by-one.

# In[8]:


stocks = stocks[~stocks['Ticker'].isin(['DISCA', 'HFC','VIAC','WLTW'])]  

final_dataframe = pd.DataFrame(columns = my_columns)

for symbol_string in symbol_strings: #[:1]:
#     print(symbol_strings)
    batch_api_call_url = f'https://cloud.iexapis.com/stable/stock/market/batch/?types=stats,quote&symbols={symbol_string}&token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
   # print(data.status_code)
    #print(data)
    for symbol in symbol_string.split(','):
            final_dataframe = final_dataframe.append(
                                        pd.Series([symbol, 
                                                   data[symbol]['quote']['latestPrice'],
                                                   data[symbol]['stats']['peRatio'],
                                                   'N/A'
                                                   ], 
                                                  index = my_columns), 
                                        ignore_index = True)
        
    
final_dataframe
 


# ## Removing Glamour Stocks
# 
# The opposite of a "value stock" is a "glamour stock". 
# 
# Since the goal of this strategy is to identify the 50 best value stocks from our universe, our next step is to remove glamour stocks from the DataFrame.
# 
# We'll sort the DataFrame by the stocks' price-to-earnings ratio, and drop all stocks outside the top 50.

# In[9]:


final_dataframe.sort_values('Price-to-Earnings Ratio', inplace = True)
final_dataframe = final_dataframe[final_dataframe['Price-to-Earnings Ratio'] > 0]
final_dataframe = final_dataframe[:50]
final_dataframe.reset_index(inplace = True)
final_dataframe.drop('index', axis=1, inplace = True)
final_dataframe


# ## Calculating the Number of Shares to Buy
# We now need to calculate the number of shares we need to buy. 
# 
# To do this, we will use the `portfolio_input` function that we created in our momentum project.
# 
# I have included this function below.

# In[10]:


def portfolio_input():
    global portfolio_size
    portfolio_size = input("Enter the value of your portfolio:")

    try:
        val = float(portfolio_size)
    except ValueError:
        print("That's not a number! \n Try again:")
        portfolio_size = input("Enter the value of your portfolio:")


# Use the `portfolio_input` function to accept a `portfolio_size` variable from the user of this script.

# In[11]:


portfolio_input()


# You can now use the global `portfolio_size` variable to calculate the number of shares that our strategy should purchase.

# In[12]:


position_size = float(portfolio_size) / len(final_dataframe.index)
for i in range(0, len(final_dataframe['Ticker'])):
    final_dataframe.loc[i, 'Number of Shares to Buy'] = math.floor(position_size / final_dataframe['Price'][i])
final_dataframe


# ## Building a Better (and More Realistic) Value Strategy
# Every valuation metric has certain flaws.
# 
# For example, the price-to-earnings ratio doesn't work well with stocks with negative earnings.
# 
# Similarly, stocks that buyback their own shares are difficult to value using the price-to-book ratio.
# 
# Investors typically use a `composite` basket of valuation metrics to build robust quantitative value strategies. In this section, we will filter for stocks with the lowest percentiles on the following metrics:
# 
# * Price-to-earnings ratio
# * Price-to-book ratio
# * Price-to-sales ratio
# * Enterprise Value divided by Earnings Before Interest, Taxes, Depreciation, and Amortization (EV/EBITDA)
# * Enterprise Value divided by Gross Profit (EV/GP)
# 
# Some of these metrics aren't provided directly by the IEX Cloud API, and must be computed after pulling raw data. We'll start by calculating each data point from scratch.

# In[13]:


symbol = 'AAPL'
batch_api_call_url = f'https://cloud.iexapis.com/stable/stock/market/batch/?types=advanced-stats,quote&symbols={symbol}&token={IEX_CLOUD_API_TOKEN}'
data = requests.get(batch_api_call_url).json()

# P/E Ratio
pe_ratio = data[symbol]['quote']['peRatio']

# P/B Ratio
pb_ratio = data[symbol]['advanced-stats']['priceToBook']

#P/S Ratio
ps_ratio = data[symbol]['advanced-stats']['priceToSales']

# EV/EBITDA
enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
ebitda = data[symbol]['advanced-stats']['EBITDA']
ev_to_ebitda = enterprise_value/ebitda

# EV/GP
gross_profit = data[symbol]['advanced-stats']['grossProfit']
ev_to_gross_profit = enterprise_value/gross_profit


# Let's move on to building our DataFrame. You'll notice that I use the abbreviation `rv` often. It stands for `robust value`, which is what we'll call this sophisticated strategy moving forward.

# In[16]:


symbol = 'AAPL'
batch_api_call_url = f'https://cloud.iexapis.com/stable/stock/market/batch/?types=advanced-stats,quote&symbols={symbol}&token={IEX_CLOUD_API_TOKEN}'
data = requests.get(batch_api_call_url).json()

# P/E Ratio
pe_ratio = data[symbol]['quote']['peRatio']

# P/B Ratio
pb_ratio = data[symbol]['advanced-stats']['priceToBook']

#P/S Ratio
ps_ratio = data[symbol]['advanced-stats']['priceToSales']

# EV/EBITDA
enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
ebitda = data[symbol]['advanced-stats']['EBITDA']
ev_to_ebitda = enterprise_value/ebitda

# EV/GP
gross_profit = data[symbol]['advanced-stats']['grossProfit']
ev_to_gross_profit = enterprise_value/gross_profit


# In[17]:


rv_columns = [
    'Ticker',
    'Price',
    'Number of Shares to Buy', 
    'Price-to-Earnings Ratio',
    'PE Percentile',
    'Price-to-Book Ratio',
    'PB Percentile',
    'Price-to-Sales Ratio',
    'PS Percentile',
    'EV/EBITDA',
    'EV/EBITDA Percentile',
    'EV/GP',
    'EV/GP Percentile',
    'RV Score'
]

rv_dataframe = pd.DataFrame(columns = rv_columns)

for symbol_string in symbol_strings:
    batch_api_call_url = f'https://cloud.iexapis.com/stable/stock/market/batch?symbols={symbol_string}&types=quote,advanced-stats&token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for symbol in symbol_string.split(','):
        enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
        ebitda = data[symbol]['advanced-stats']['EBITDA']
        gross_profit = data[symbol]['advanced-stats']['grossProfit']
        
        try:
            ev_to_ebitda = enterprise_value/ebitda
        except TypeError:
            ev_to_ebitda = np.NaN
        
        try:
            ev_to_gross_profit = enterprise_value/gross_profit
        except TypeError:
            ev_to_gross_profit = np.NaN
            
        rv_dataframe = rv_dataframe.append(
            pd.Series([
                symbol,
                data[symbol]['quote']['latestPrice'],
                'N/A',
                data[symbol]['quote']['peRatio'],
                'N/A',
                data[symbol]['advanced-stats']['priceToBook'],
                'N/A',
                data[symbol]['advanced-stats']['priceToSales'],
                'N/A',
                ev_to_ebitda,
                'N/A',
                ev_to_gross_profit,
                'N/A',
                'N/A'
        ],
        index = rv_columns),
            ignore_index = True
        )


# ## Dealing With Missing Data in Our DataFrame
# 
# Our DataFrame contains some missing data because all of the metrics we require are not available through the API we're using. 
# 
# You can use pandas' `isnull` method to identify missing data:

# In[18]:


rv_dataframe[rv_dataframe.isnull().any(axis=1)]


# Dealing with missing data is an important topic in data science.
# 
# There are two main approaches:
# 
# * Drop missing data from the data set (pandas' `dropna` method is useful here)
# * Replace missing data with a new value (pandas' `fillna` method is useful here)
# 
# In this tutorial, we will replace missing data with the average non-`NaN` data point from that column. 
# 
# Here is the code to do this:

# In[19]:


for column in ['Price-to-Earnings Ratio', 'Price-to-Book Ratio','Price-to-Sales Ratio',  'EV/EBITDA','EV/GP']:
    rv_dataframe[column].fillna(rv_dataframe[column].mean(), inplace = True)


# Now, if we run the statement from earlier to print rows that contain missing data, nothing should be returned:

# In[20]:


rv_dataframe[rv_dataframe.isnull().any(axis=1)]


# ## Calculating Value Percentiles
# 
# We now need to calculate value score percentiles for every stock in the universe. More specifically, we need to calculate percentile scores for the following metrics for every stock:
# 
# * Price-to-earnings ratio
# * Price-to-book ratio
# * Price-to-sales ratio
# * EV/EBITDA
# * EV/GP
# 
# Here's how we'll do this:

# In[21]:


metrics = {
            'Price-to-Earnings Ratio': 'PE Percentile',
            'Price-to-Book Ratio':'PB Percentile',
            'Price-to-Sales Ratio': 'PS Percentile',
            'EV/EBITDA':'EV/EBITDA Percentile',
            'EV/GP':'EV/GP Percentile'
}

for row in rv_dataframe.index:
    for metric in metrics.keys():
        rv_dataframe.loc[row, metrics[metric]] = stats.percentileofscore(rv_dataframe[metric], rv_dataframe.loc[row, metric])/100

# Print each percentile score to make sure it was calculated properly
for metric in metrics.values():
    print(rv_dataframe[metric])

#Print the entire DataFrame    
rv_dataframe


# ## Calculating the RV Score
# We'll now calculate our RV Score (which stands for Robust Value), which is the value score that we'll use to filter for stocks in this investing strategy.
# 
# The RV Score will be the arithmetic mean of the 4 percentile scores that we calculated in the last section.
# 
# To calculate arithmetic mean, we will use the mean function from Python's built-in statistics module.

# In[22]:


from statistics import mean

for row in rv_dataframe.index:
    value_percentiles = []
    for metric in metrics.keys():
        value_percentiles.append(rv_dataframe.loc[row, metrics[metric]])
    rv_dataframe.loc[row, 'RV Score'] = mean(value_percentiles)
    
rv_dataframe


# ## Selecting the 50 Best Value Stocks¶
# 
# As before, we can identify the 50 best value stocks in our universe by sorting the DataFrame on the RV Score column and dropping all but the top 50 entries.

# In[24]:


rv_dataframe.sort_values(by = 'RV Score', inplace = True)
rv_dataframe = rv_dataframe[:50]
rv_dataframe.reset_index(drop = True, inplace = True)
rv_dataframe


# ## Calculating the Number of Shares to Buy
# We'll use the `portfolio_input` function that we created earlier to accept our portfolio size. Then we will use similar logic in a for loop to calculate the number of shares to buy for each stock in our investment universe.

# In[25]:


portfolio_input()


# In[26]:


position_size = float(portfolio_size) / len(rv_dataframe.index)
for i in range(0, len(rv_dataframe['Ticker'])-1):
    rv_dataframe.loc[i, 'Number of Shares to Buy'] = math.floor(position_size / rv_dataframe['Price'][i])
rv_dataframe


# ## Formatting Our Excel Output
# 
# We will be using the XlsxWriter library for Python to create nicely-formatted Excel files.
# 
# XlsxWriter is an excellent package and offers tons of customization. However, the tradeoff for this is that the library can seem very complicated to new users. Accordingly, this section will be fairly long because I want to do a good job of explaining how XlsxWriter works.

# In[27]:


writer = pd.ExcelWriter('value_strategy.xlsx', engine='xlsxwriter')
rv_dataframe.to_excel(writer, sheet_name='Value Strategy', index = False)


# ## Creating the Formats We'll Need For Our .xlsx File
# You'll recall from our first project that formats include colors, fonts, and also symbols like % and $. We'll need four main formats for our Excel document:
# 
# * String format for tickers
# * \$XX.XX format for stock prices
# * \$XX,XXX format for market capitalization
# * Integer format for the number of shares to purchase
# * Float formats with 1 decimal for each valuation metric
# 
# Since we already built some formats in past sections of this course, I've included them below for you. Run this code cell before proceeding.

# In[28]:


background_color = '#0a0a23'
font_color = '#ffffff'

string_template = writer.book.add_format(
        {
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )

dollar_template = writer.book.add_format(
        {
            'num_format':'$0.00',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )

integer_template = writer.book.add_format(
        {
            'num_format':'0',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )

float_template = writer.book.add_format(
        {
            'num_format':'0',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )

percent_template = writer.book.add_format(
        {
            'num_format':'0.0%',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )


# In[29]:


column_formats = {
                    'A': ['Ticker', string_template],
                    'B': ['Price', dollar_template],
                    'C': ['Number of Shares to Buy', integer_template],
                    'D': ['Price-to-Earnings Ratio', float_template],
                    'E': ['PE Percentile', percent_template],
                    'F': ['Price-to-Book Ratio', float_template],
                    'G': ['PB Percentile',percent_template],
                    'H': ['Price-to-Sales Ratio', float_template],
                    'I': ['PS Percentile', percent_template],
                    'J': ['EV/EBITDA', float_template],
                    'K': ['EV/EBITDA Percentile', percent_template],
                    'L': ['EV/GP', float_template],
                    'M': ['EV/GP Percentile', percent_template],
                    'N': ['RV Score', percent_template]
                 }

for column in column_formats.keys():
    writer.sheets['Value Strategy'].set_column(f'{column}:{column}', 25, column_formats[column][1])
    writer.sheets['Value Strategy'].write(f'{column}1', column_formats[column][0], column_formats[column][1])


# ## Saving Our Excel Output
# As before, saving our Excel output is very easy:

# In[30]:


writer.save()


# In[ ]:




