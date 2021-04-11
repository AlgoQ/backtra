from strategies.GoldenCross2 import GoldenCross
from utils import jsonToOhlcv

# Include all variable values in the params
params = {'sma1': 50, 'sma2': 200, 'atr': 14, 'tpMultipier': 2, 'slMultipier': 5, 'maxLossPerc': 2, 'leverage': 2}
timeframe = '30T'

# Convert json data file to 30min ohlcv dataframe
ohlcv = jsonToOhlcv(r'/run/media/kobej/D/histCryptoDatafeed/data/ohlcv_ftx_AAVEPERP_179days.json', timeframe)

precision = round(ohlcv['close'].apply(lambda x: len(str(x).split('.')[-1])).mean())
pip = float('0.' + ('0' * (precision - 1)) + '1')

ohlcvs = {}
ohlcvs['precision'] = precision
ohlcvs['pip'] = pip
ohlcvs[timeframe] = ohlcv

goldenCross = GoldenCross(
    strategyName = 'GoldenCross',
    symbol = 'AAVE-PERP',
    params= params,
    ohlcvs = ohlcvs,
    timeFrames = [timeframe],
    tradeLogs = True
)

goldenCross.run()

results = goldenCross.calcResults()
goldenCross.showResults(results)