import requests
import random
from datetime import datetime, timedelta, date
from pymongo import MongoClient
from google.cloud import secretmanager
import yfinance as yf

secrets_client = secretmanager.SecretManagerServiceClient()
secrets_name = secrets_client.secret_version_path("162543004095", "mongodb-pswd", "1")
secret_response = secrets_client.access_secret_version(secrets_name)
mongo_psw = secret_response.payload.data.decode('UTF-8')

client = MongoClient("mongodb+srv://trader:{}@ahmed-3jokf.gcp.mongodb.net/test?retryWrites=true&w=majority".format(
    mongo_psw))

DATA = []

db = client.prices
for d in db.daily.find():
    DATA.append(d)

print("First %d rows of data\n" % (min(3, len(DATA))))
for i in range(min(3, len(DATA))):
         print(DATA[i])

DATA = DATA[len(DATA) - 1 ] 

# TODO add comment about each variables
COMFORTABLE_PRICE_TO_BUY = .2
EXPECTED_MIN_PROFIT_LEVEL = 1.1 
TIME_HORIZON_IN_DAYS = 365
PRECISION_FOR_TIME_HORIZON = 50  # ok to buy within +/- of this time horizon
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
        option = Option(target_price, date + timedelta(days=TIME_HORIZON_IN_DAYS), option_price)
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
        probability = self._probability(TIME_HORIZON_IN_DAYS, price_percent_delta)
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
    # Specify the budget 
    trading_strategy = BasicTradingStrategy(500)
    date = datetime.today()
    # price is just one price for that day
    price = DATA["price"]
    
    options = get_options()
    trading_strategy.new_day(date, price, options)
    print("#### {} DAY ENDS ####, money: {}".format(0, trading_strategy.budget + trading_strategy.calculate_portfolio_price(price)))

def trade(context, input_obj):
    main()
    print(":)!")
    return ":)!"

def get_options():
    today = date.today()
    min_date = today + timedelta(days=TIME_HORIZON_IN_DAYS - PRECISION_FOR_TIME_HORIZON)
    max_date = today + timedelta(days=TIME_HORIZON_IN_DAYS + PRECISION_FOR_TIME_HORIZON)

    dates = []

    for opt in fb.options:
        option_date = datetime.strptime(opt, "%Y-%m-%d").date()
        if option_date >= min_date and option_date <= max_date:
            dates.append(option_date)

    print("Dates that exist for the ticket and your time horizon: {}".format(str(dates)))
    options = []

    for experation_date in dates:
        call_fb_options, _ = fb.option_chain(EXPIRATION_DATE)
        print(call_fb_options)
        for option in call_fb_options.iterrows():
            print(option)
            option_price = option["lastPrice"]
            options.append((option_price, Option(option["strike"], experation_date, option_price)))
    return options