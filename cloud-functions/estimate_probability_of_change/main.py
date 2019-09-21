import os
import base64

from google.cloud import kms
from pymongo import MongoClient
import urllib

REQUEST_KEY_NAME = "name"
REQUEST_KEY_DURATION_IN_DAYS = "days"
REQUEST_KEY_PERCENT_CHANGE = "percent_change"
REQUESTS = "requests"


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
    if ws < 0:
        raise ValueError("Time windows can not be negative")
    if len(prices) < ws:
        ValueError("There is not enough data to support window size %s", ws)

    up = 0
    down = 0
    for i in range(len(prices) - ws + 1):
        newPercentChange = calculate_percent_chage(
            prices[i], prices[i + ws - 1])
        if newPercentChange >= percent:
            up = up + 1
        else:
            down = down + 1
    # flip the operation if request is for negative number
    if percent > 0:
        ans = (up * 100.0) / (up + down)
    else:
        ans = (down * 100.0) / (up + down)
    return ans


def calculate_batch_likelyhood(prices, percent, ws):
    """
    prices: List of prices for specific stock
    percent: List of percent change user expect to happen
    ws: List of window size in term of days
    """
    if len(percent) != len(ws):
        print("Invalid input percent size",
              len(percent),
              ", time window size",
              len(ws))
        return [0]
    result = []
    # TODO: Can we parallelize the below code
    for i in range(len(percent)):
        result.append(calculate_likelyhood(prices, percent[i], ws[i]))
    return result


def estimate_probability_of_change(request):
    request_json = request.get_json(silent=True)
    request_json = request_json if request_json else dict()
    name = request_json.get(REQUEST_KEY_NAME, "FB")
    duration_in_days = request_json.get(REQUEST_KEY_DURATION_IN_DAYS, 2)
    percent_change = request_json.get(REQUEST_KEY_PERCENT_CHANGE, 2)

    daily_prices = DB.daily
    prices = [result["price"] for result in daily_prices.find({"name": name})]

    return str(calculate_likelyhood(prices, percent_change, duration_in_days))


def batch_estimate_probability_of_change(request):
    request_json = request.get_json(silent=True)
    request_json = request_json if request_json else dict()
    requests = request_json.get(REQUESTS, [])
    price_cache = {}
    results = []
    for i in range(len(requests)):
        name = requests[i]["name"]
        days = requests[i]["days"]
        percent_change = requests[i]["percent_change"]
        prices = []
        # Get from cache if available
        if name in price_cache.keys():
            prices = price_cache[name]
        else:
            daily_prices = DB.daily
            prices = [result["price"] for result in daily_prices.find({
                "name": name})]
            # Store in the cache
            price_cache[name] = prices
        results.append(
            calculate_batch_likelyhood(prices, percent_change, days))
    assert(len(results) == len(requests))
    return str(results)
