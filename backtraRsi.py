from strategies.RsiStrategy import RsiStrategy
from utils import jsonToOhlcv

params = {'rsi': 14}

timeframe = '5T'

histTrades = ohlcv = jsonToOhlcv(r'fileLocation', timeframe)

exampleStrat = RsiStrategy(
    strategyName='ExampleStrategy',
    symbol = 'AAVE/USDT',
    params= params,
    histTrades= histTrades,
    timeFrames= [timeframe]
)