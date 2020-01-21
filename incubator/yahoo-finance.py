import yfinance as yf

msft = yf.Ticker("MSFT")

print(" get stock info")
print(msft.info)

print(" get historical market data")
hist = msft.history(period="max")
print(hist)
print(" show actions (dividends, splits)")
print(msft.actions)

print(" show dividends")
print(msft.dividends)

print(" show splits")
print(msft.splits)

print(" show financials")
print(msft.financials)
print("quaterly financials")
print(msft.quarterly_financials)

print(" show major holders")
print(msft.major_holders)

print(" show institutional holders")
print(msft.institutional_holders)

print(" show balance heet")
print(msft.balance_sheet)
print(" quarterly balance sheet")
print(msft.quarterly_balance_sheet)

print(" show cashflow")
print(msft.cashflow)
print(" quarterly cashflow")
print(msft.quarterly_cashflow)

print(" show earnings")
print(msft.earnings)
print(" quarterly earnings")
print(msft.quarterly_earnings)

print(" show sustainability")
print(msft.sustainability)

print(" show analysts recommendations")
print(msft.recommendations)

print(" show next event (earnings, etc)")
print(msft.calendar)

# show ISIN code - *experimental*
# ISIN = International Securities Identification Number
print("isin")
print(msft.isin)

print("show options expirations")
print(msft.options)

print(" get option chain for specific expiration")
opt = msft.option_chain('2020-01-30')
print(opt)
# data available via: opt.calls, opt.puts
