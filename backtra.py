from strategies.ExampleStrategy import ExampleStrategy
from utils import fetchFolder

params = {'sma1': 50, 'sma2': 200, 'atr': 14}

histTrades = fetchFolder(r'/run/media/kobej/B204D33B04D300F1/Work/backtra/data/AAVEUSDT')

exampleStrat = ExampleStrategy(
    strategyName='ExampleStrategy',
    symbol = 'AAVE/USDT',
    params= params,
    histTrades= histTrades,
    timeFrames= ['1T'],
    tpMultipier= 2,
    slMultipier= 1,
    maxLossPerc= 2
)

exampleStrat.run()
exampleStrat.showResults()