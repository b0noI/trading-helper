# This program gets the price for given ticket and given date

import yfinance as yf
import datetime 
import sys
from datetime import date, timedelta


TICKER = "FB"
DATE =  str(date.today())
FUTURE_DATE = "2020-12-31"

Today = datetime.datetime(int(DATE[:4]), int(DATE[5:7]), int(DATE[8:]))
Future_date = datetime.datetime(int(FUTURE_DATE[:4]), int(FUTURE_DATE[5:7]), int(FUTURE_DATE[8:]))

ticker = yf.Ticker(TICKER)
opt = [] 

# options might not have price for every day including today.
# So I am finding nearest day in future when price for option exist.
# opt[0] is CALL of type DATA Frame
# opt[1] is PUT of type  DATA Frame
while True: 
  print("Trying for " + str(Today))
  try:
    opt = ticker.option_chain(Today.strftime('%Y-%m-%d'))
    break
  except ValueError:
    # Find a day in future where prices exist 
    Today = Today + timedelta(days=1)

print(Today)
#print(opt)

call = opt[0]
put = opt[1]
# There is possibility that there is no price available for given DATE.
# This program will find the next immediate available option price for PUT and print it.
final_date = FUTURE_DATE
final_price = sys.maxsize

# Currently it just look for closes date and gets the price
# TODO: Find smallest prices in closest date 
for index, row in put.iterrows():
    Date = str(row['lastTradeDate'])
    Date = Date[:10]
    d = datetime.datetime(int(Date[:4]), int(Date[5:7]), int(Date[8:]))
    if d >= Today and d < Future_date:
      final_date = str(d)
      final_price = row['lastPrice']
print(final_date)
print(final_price)
