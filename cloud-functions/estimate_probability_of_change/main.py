import os
import base64

from google.cloud import kms
from pymongo import MongoClient
import urllib
import numpy


KMS_CLIENT = kms.KeyManagementServiceClient()
db_pass = KMS_CLIENT.decrypt(
    os.environ["SECRET_RESOURCE_NAME"],
    base64.b64decode(os.environ["SECRET_STRING"]),
).plaintext
MONGO_CLIENT = MongoClient('mongodb+srv://trader:' +
                           urllib.parse.quote_plus(db_pass) +
                           '@ahmed-3jokf.gcp.mongodb.net/test')
DB = MONGO_CLIENT['prices']



def calculatePercentChage(oldval, newval):
    return (((newval - oldval) * 100.0)/oldval)

"""
   prices: list of prices for specific stock
   percent: percent change user expect to happen
   ws: Window size in term of days
"""
def calCulateLikelyHood(prices, percent, ws):
    if len(prices) < ws: 
       percentChange = calculatePercentChage(prices[0], prices[len(prices.size()-1)])
       return percentchange >= percent
    
    up = 0 
    down = 0 
    for i in range(len(prices) - ws + 1): 
        newPercentChange = calculatePercentChage(prices[i], prices[i+ws - 1]) 
        if newPercentChange > percent:
           up = up + 1 
        else:
           down = down + 1 

    return (up*100.0)/(up+down)


def estimate_probability_of_change(request):
    daily_prices = DB.daily
    results = daily_prices.find({'name': 'FB'})
    prices = [] 
    for result in results:
        prices.append(result["price"])

    # 2 % change in last 3 days
    return str(calCulateLikelyHood(prices, 2, 3))
