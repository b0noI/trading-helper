from datetime import timedelta, date, datetime

import yfinance as yf

# CASE 1: for estimating price of an option that you have already
# Let's assume I have in my portfolio FB option that:
# * expires on 2020-12-17
# * has strike value 230
# and I want to check how much this option costs today to determine if I need to sell or not

TICKER = "FB"
EXPIRATION_DATE = "2020-12-17"
STRIKE_PRICE = 230.0

fb = yf.Ticker(TICKER)
call_fb_options, _ = fb.option_chain(EXPIRATION_DATE)
call_fb_option = call_fb_options[call_fb_options["strike"] == STRIKE_PRICE]
price = call_fb_option["lastPrice"].values[0]

print("Current price of your option is {}".format(price))

# CASE 2: for estimating prices if we need to buy or not
TIME_HORIZON_IN_DAYS = 365
PRECISION_FOR_TIME_HORIZON = 50  # ok to buy within +/- of this time horizon

today = date.today()
min_date = today + timedelta(days=TIME_HORIZON_IN_DAYS - PRECISION_FOR_TIME_HORIZON)
max_date = today + timedelta(days=TIME_HORIZON_IN_DAYS + PRECISION_FOR_TIME_HORIZON)

dates = []

for opt in fb.options:
    option_date = datetime.strptime(opt, "%Y-%m-%d").date()
    if option_date >= min_date and option_date <= max_date:
        dates.append(option_date)

print("Dates that exist for the ticket and your time horizon: {}".format(str(dates)))

for experation_date in dates:
    call_fb_options, _ = fb.option_chain(EXPIRATION_DATE)
    print(call_fb_options)
