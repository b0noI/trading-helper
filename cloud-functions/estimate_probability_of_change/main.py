import os
import base64

from google.cloud import kms
from pymongo import MongoClient
import urllib

REQUEST_KEY_NAME = "name"
REQUEST_KEY_DURATION_IN_DAYS = "days"
REQUEST_KEY_PERCENT_CHANGE = "percent_change"

KMS_CLIENT = kms.KeyManagementServiceClient()
db_pass = KMS_CLIENT.decrypt(
    os.environ["SECRET_RESOURCE_NAME"],
    base64.b64decode(os.environ["SECRET_STRING"]),
).plaintext
MONGO_CLIENT = MongoClient('mongodb+srv://trader:' +
                           urllib.parse.quote_plus(db_pass) +
                           '@ahmed-3jokf.gcp.mongodb.net/test')
DB = MONGO_CLIENT['prices']


def calculate_percent_chage(oldval, newval):
    return (((newval - oldval) * 100.0)/oldval)


def calculate_likelyhood(prices, percent, ws):
    """
    prices: list of prices for specific stock
    percent: percent change user expect to happen
    ws: Window size in term of days
    """
    if len(prices) < ws:
        percentChange = calculate_percent_chage(prices[0],
                                                prices[len(prices.size() - 1)])
        return percentChange >= percent

    up = 0
    down = 0
    for i in range(len(prices) - ws + 1):
        newPercentChange = calculate_percent_chage(prices[i], prices[i+ws - 1])
        if newPercentChange > percent:
            up = up + 1
        else:
            down = down + 1

    return (up * 100.0)/(up + down)


def estimate_probability_of_change(request):
    request_json = request.get_json(silent=True)
    request_json = request_json if request_json else dict()
    name = request_json.get(REQUEST_KEY_NAME, "FB")
    duration_in_days = request_json.get(REQUEST_KEY_DURATION_IN_DAYS, 2)
    percent_change = request_json.get(REQUEST_KEY_PERCENT_CHANGE, 2)

    daily_prices = DB.daily
    prices = [result["price"] for result in daily_prices.find({"name": name})]

    return str(calculate_likelyhood(prices, percent_change, duration_in_days))
