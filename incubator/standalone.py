import requests
import numpy as np
import matplotlib.pyplot as plt
import random
from datetime import datetime, timedelta
from IPython.display import clear_output
from pymongo import MongoClient
from bson import ObjectId


client = MongoClient("mongodb+srv://trader:my-password@ahmed-3jokf.gcp.mongodb.net/test?retryWrites=true&w=majority")

# DB related operation 
# TODO add them into a class

## Portfolio DB
PORTFOLIO = []

portfolio_db = client.portfolio
# For a given portfolio (lastportfolio) there should be only one entry.
for d in portfolio_db.lastportfolio.find():
    PORTFOLIO.append(d)

PORTFOLIO = PORTFOLIO[len(PORTFOLIO) - 1 ]
# Delete the row from DB 
def delete_row(collection_id):
   portfolio_db.lastportfolio.delete_one({'_id': ObjectId(collection_id)})

# Insert new row to DB
def insert_new_price(history_price, current_price):
   if history_price is None:
      print("Database needs to have a initial portfolio value")
      exit(-1)
   history_price.append({ datetime.today().strftime('%Y-%m-%d-%H:%M:%S') : current_price})
   portfolio_db.lastportfolio.insert_one({'history_price':history_price, 'current_price': current_price})
    

## Stock price DB
STOCK = []

price_db = client.prices
for d in price_db.daily.find():
    STOCK.append(d)

STOCK = STOCK[len(STOCK) - 1 ] 

# TODO add comment about each variables
COMFORTABLE_PRICE_TO_BUY = .2
EXPECTED_MIN_PROFIT_LEVEL = 1.1
DAYS_TIME_HORIZON = 300
LIKELIHOOD_THRESHOLD_TO_SELL = 0.6
PERCENT_DEFINETLY_SELL = 120.

URL_SINGLE = "https://us-central1-trading-systems-252219.cloudfunctions.net/estimate_probability_of_change"

REQUESTS_FIELD_NAME = "requests"
TICKER_FIELD_NAME = "name"
FACEBOOK_TICKER_NAME = "FB"
DURATION_DAYS_FIELD_NAME = "days"
PERCENT_CHANGE_FIELD_NAME = "percent_change"

DEBUG = False

class Option(object):
    
    def __init__(self, target_price, target_date, original_price):
        self.target_price = target_price
        self.target_date = target_date
        self.original_price = original_price
        
    def __str__(self):
        return "Option for target_price: {}, for date: {}".format(self.target_price, self.target_date)

class BasicTradingStrategy(object):
    
    def __init__(self, budget):
        self.budget = budget
        self.portfolio = []
        
    def new_day(self, date, price, avilable_options):
        for option_data in avilable_options:
            option_price, option = option_data
            self._decide_if_to_buy(date, price, option_price, option.target_price)
        
    
    def _buy(self, date, option_price, target_price):
        self.budget -= option_price
        option = Option(target_price, date + timedelta(days=DAYS_TIME_HORIZON), option_price)
        self.portfolio.append(option)
        if DEBUG:
            print("buy: {}".format(option))
    
    def _probability(self, days_delta, price_percent_delta):
        request_to_server = {
            TICKER_FIELD_NAME: FACEBOOK_TICKER_NAME,
            DURATION_DAYS_FIELD_NAME: days_delta,
            PERCENT_CHANGE_FIELD_NAME: price_percent_delta
        }
        response = requests.post(url=URL_SINGLE, json=request_to_server)
        if response.status_code != 200:
            raise ValueError("Backend response is: {} while expected code 200".format(str(response)))
        return response.json()
    
    def _decide_if_to_buy(self, date, current_price, option_price, option_target_price):
        break_even_price = option_price + option_target_price
        expected_profit_price = EXPECTED_MIN_PROFIT_LEVEL * break_even_price
        price_percent_delta = (expected_profit_price / current_price) * 100 - 100
        probability = self._probability(DAYS_TIME_HORIZON, price_percent_delta)
        if probability > LIKELIHOOD_THRESHOLD_TO_SELL:
            if self.budget > option_price:
                self._buy(date, option_price, option_target_price)
                
    def _sell(self, i, price):
        option = self.portfolio[i]
        # TODO
        current_option_price = self._calculate_option_price(option, price)
        self.budget += current_option_price
        del self.portfolio[i]
        
    def _calculate_option_price(self, option, price):
        delta = (option.target_price + option.original_price) - price
        if delta > 0:
            return delta
        else:
            return price * 0.1
        
    def calculate_portfolio_price(self, price):
        total_price = 0
        for option in self.portfolio:
            total_price += self._calculate_option_price(option, price)
        return total_price
                
    def _maybe_sell(self, current_price):
        today = datetime.now()
        for option in self.portfolio:
            delta = option.target_date - today
            days_delta = delta.days
            break_even_price = option.original_price + option.target_price
            expected_profit_price = EXPECTED_MIN_PROFIT_LEVEL * break_even_price
            price_percent_delta = (expected_profit_price / current_price) * 100 - 100
            if price_percent_delta > PERCENT_DEFINETLY_SELL:
                if DEBUG:
                    print("Selling since % delta is high: {}".format(price_percent_delta))
                self._sell(i)
            if i > 0:
                i -= 1
            elif days_delta <= 1:
                if DEBUG:
                    print("Selling since expired")
                self._sell_option(i)
                if i > 0:
                    i -= 1
            ## 
            elif price_percent_delta >= 100.:
                if DEBUG:
                    print("Not selling since profitable but not much")
            else:
                if DEBUG:
                    print("deciding if to sell")
            request_to_server = {
                TICKER_FIELD_NAME: FACEBOOK_TICKER_NAME,
                DURATION_DAYS_FIELD_NAME: days_delta,
                PERCENT_CHANGE_FIELD_NAME: price_percent_delta
            }
            response = requests.post(url=URL_SINGLE, json=request_to_server)
            if response.status_code != 200:
                raise ValueError("Backend response is: {} while expected code 200".format(str(response)))
            likelihood = response.json()
            if DEBUG:
                print("likelihood to profit: {}".format(likelihood))
            if likelihood < LIKELIHOOD_THRESHOLD_TO_SELL: 
                print("selling")
                self._sell(i)
                if i > 0:
                    i -= 1

                    
def main():
    # Get the budget from DB
    budget = PORTFOLIO["current_price"]
    print("Performing trading with budget {}".format(budget))
    # Specify the budget 
    trading_strategy = BasicTradingStrategy(budget)
    date = datetime.today()
    # Price is just one price for that day of stock
    price = STOCK["price"]
    # TODO: Currently we are generating random option price, but plug in here real option data 
    option_price = ((0.2 * random.random()) + 0.1) * price
    # Target price, target date (a future date), original option price
    new_option = Option(price * 1.1, date + timedelta(days=300), option_price)
    trading_strategy.new_day(date, price, [(option_price, new_option)])
    print("new budget: {}".format(trading_strategy.budget + trading_strategy.calculate_portfolio_price(price)))
    # Update DB with new budget and trading history
    insert_new_price(PORTFOLIO['history_price'], trading_strategy.budget + trading_strategy.calculate_portfolio_price(price))
    # Delete the old old budget  
    delete_row(PORTFOLIO['_id'])

main()
