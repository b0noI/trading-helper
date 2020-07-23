import requests
import random
import constants
from datetime import datetime, timedelta, date
from pymongo import MongoClient
from bson import ObjectId
from google.cloud import secretmanager
import yfinance as yf
from yahoo_fin import stock_info as si

secrets_client = secretmanager.SecretManagerServiceClient()
secrets_name = secrets_client.secret_version_path("162543004095", "mongodb-pswd", "1")
secret_response = secrets_client.access_secret_version(secrets_name)
mongo_psw = secret_response.payload.data.decode('UTF-8')

client = MongoClient("mongodb+srv://trader:{}@ahmed-3jokf.gcp.mongodb.net/test?retryWrites=true&w=majority".format(mongo_psw))

portfolios_collection = client.portfolio


def initiate_budget_amount():
    portfolio_count = portfolios_collection.portfolios.find({"name": constants.PORTFOLIO_NAME}).count()
    if portfolio_count == 1:
        return
    elif portfolio_count > 1:
        raise ValueError("there are more than one portfolio with this name")

    portfolios_collection.portfolios.insert_one({"name": constants.PORTFOLIO_NAME, constants.CURRENT_BUDGET_FIELD_NAME: 5000})


# Return total cash you have available for trading. 
def get_current_portfolio_price():
    return portfolios_collection.portfolios.find_one({"name": constants.PORTFOLIO_NAME})[constants.CURRENT_BUDGET_FIELD_NAME]


def set_current_portfolio_price(price):
    portfolios_collection.portfolios.update_one({
        "name": constants.PORTFOLIO_NAME
    }, {
        "$set": {
            constants.CURRENT_BUDGET_FIELD_NAME: price
        }
    })

# If we have bought any options before, lets restore them from DB 
def get_list_of_bought_options():
    portfolio = []    
    for item in portfolios_collection.lastportfolio.find():
        item.pop('_id') # Hack to remove mongoDB part 
        # Convert item dict to Option object 
        opt = Option(item['target_price'], item['target_date'], item['original_price'])      
        portfolio.append(opt) 
    return portfolio

# Store list of bought options to database
def store_list_of_bought_options(portfolio):
    # Check if we have something in DB if so delete them please 
    bought_portfolio_count = portfolios_collection.lastportfolio.count()
    if bought_portfolio_count != 0:
    	portfolios_collection.lastportfolio.remove()

    # serialized the portfolio and store to the db
    serialized_portfolio = []
    for i in range(len(portfolio)):
        serialized_portfolio.append(dict(portfolio[i]))
    portfolios_collection.lastportfolio.insert(serialized_portfolio)     

initiate_budget_amount()

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

DEBUG = True


class Option(object):
    
    def __init__(self, target_price, target_date, original_price):
        self.target_price = target_price
        self.target_date = target_date
        self.original_price = original_price

    def __iter__(self):
       yield 'target_price', self.target_price
       yield 'target_date', self.target_date 
       yield 'original_price', self.original_price
     
    def __str__(self):
        return "Option for target_price: {}, for date: {}".format(self.target_price, self.target_date)


class BasicTradingStrategy(object):
    
    def __init__(self):
        # TODO: Retrieve this from db or instantiate with emtpy list
        self.portfolio = []
     
    def new_day(self, date, price, available_options):
        for option_data in available_options:
            option_price, option = option_data
            print("target_date: {}".format(option.target_date))
            self._decide_if_to_buy(date, price, option_price, option.target_price)
    
    def _buy(self, date, option_price, target_price):
        set_current_portfolio_price(get_current_portfolio_price() - option_price)
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
        print("target date: {}".format(str(date)))
        print("deciding if to buy option with price: {}, option_target_price: {}. And current FB price is: {}".format(
            str(option_price), str(option_target_price), str(current_price)))
        break_even_price = option_price + option_target_price
        print("break_even_price: {}".format(str(break_even_price)))
        expected_profit_price = EXPECTED_MIN_PROFIT_LEVEL * break_even_price
        print("expected_profit_price: {}".format(str(expected_profit_price)))
        price_percent_delta = (expected_profit_price / current_price) * 100 - 100
        print("price_percent_delta: {}".format(str(price_percent_delta)))
        probability = self._probability(TIME_HORIZON_IN_DAYS, price_percent_delta)
        # Looks like there is a bug in our logic
        probability = probability / 100

        profit = (expected_profit_price - current_price) * probability
        print("profit value: {}, need to pay: {}".format(profit, option_price))
        print("probability: {}".format(str(probability)))
        if profit > option_price:
            print("looks like nice idea to buy")
            if probability > LIKELIHOOD_THRESHOLD_TO_SELL:
                print("looks like nice option since probability {} is higher than a threshold: {}".format(
                    str(probability), str(LIKELIHOOD_THRESHOLD_TO_SELL)))
                if get_current_portfolio_price() > option_price:
                    print("looks like we have money to buy, our current buying power: {}".format(
                        str(get_current_portfolio_price())))
                    self._buy(date, option_price, option_target_price)
     
    def _sell(self, i, price):
        option = self.portfolio[i]
        current_option_price = self._calculate_option_price(option, price)
        set_current_portfolio_price(get_current_portfolio_price() + current_option_price)
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
        for i in range(len(self.portfolio)):
            option = self.portfolio[i]
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
                self._sell(i)
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
    print("function initiated")
    # Specify the budget 
    trading_strategy = BasicTradingStrategy()
    date = datetime.today()
    # populate the last bought options to the list
    trading_strategy.portfolio = get_list_of_bought_options()
    # Price is just one price for that day of stock
    price = si.get_live_price(FACEBOOK_TICKER_NAME)
    trading_strategy.new_day(date, price, get_options())
    print("new budget: {}".format(get_current_portfolio_price() + trading_strategy.calculate_portfolio_price(price)))
    store_list_of_bought_options(trading_strategy.portfolio)


def trade(context, input_obj):
    main()


TICKER = "FB"


def get_options():
    fb = yf.Ticker(TICKER)
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

    for expiration_date in dates:
        print("checking options for expiration date: {}".format(str(expiration_date)))
        call_fb_options, _ = fb.option_chain(str(expiration_date))
        for option in call_fb_options.iterrows():
            # print("option: {}".format(str(option)))
            _, option = option
            option_price = option["lastPrice"]
            print("price found: {}".format(str(option_price)))
            options.append((option_price, Option(option["strike"], expiration_date, option_price)))
    return options


if "__main__" == __name__:
    main()
