import os
import base64

from google.cloud import kms
from pymongo import MongoClient
import urllib


KMS_CLIENT = kms.KeyManagementServiceClient()
db_pass = KMS_CLIENT.decrypt(
    os.environ["SECRET_RESOURCE_NAME"],
    base64.b64decode(os.environ["SECRET_STRING"]),
).plaintext
MONGO_CLIENT = MongoClient('mongodb+srv://trader:' +
                           urllib.parse.quote_plus(db_pass) +
                           '@ahmed-3jokf.gcp.mongodb.net/test')
DB = MONGO_CLIENT['prices']


def estimate_probability_of_change(request):
    daily_prices = DB.daily
    results = daily_prices.find({'name': 'FB'})
    for result in results:
        return str(result)
    return ""