class OptionContract(object):

  def __init__(self, ticker, option_type, target_price, expiration_date, contract_price):
    """

    :param ticker: name of the ticker (example: FB)
    :type ticker: string
    :param option_type: type can be RIGHT_TO_BUY or RIGHT_TO_SELL
    :type option_type: str
    :param target_price: price
    :type option_type: float
    :param expiration_date: date when option expires
    :type expiration_date: datetime
    :param contract_price: price for this contract
    :type contract_price: float
    """
    self.ticker = ticker
    self.option_type = option_type
    self.target_price = target_price
    self.target_date = expiration_date
    self.contract_price = contract_price

  def __str__(self):
    return (f"OptionContract(ticker: {self.ticker}, "
            f"option_type: {self.option_type}, "
            f"target_price: {self.target_price}, "
            f"target_date: {self.target_date})")
