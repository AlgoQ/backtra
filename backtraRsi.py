from strategies.RsiStrategy import RsiStrategy
from utils import jsonToOhlcv

params = {'rsi': 14, 'leverage': 1}
timeframe = '1H'

ohlcv = jsonToOhlcv(r'/run/media/kobej/D/histCryptoDatafeed/data/ohlcv_ftx_AAVEPERP_179days.json', timeframe)

precision = round(ohlcv['close'].apply(lambda x: len(str(x).split('.')[-1])).mean())
pip = float('0.' + ('0' * (precision - 1)) + '1')

ohlcvs = {}
ohlcvs['precision'] = precision
ohlcvs['pip'] = pip
ohlcvs[timeframe] = ohlcv

rsiStrat = RsiStrategy(
    strategyName='RsiStrategy',
    symbol = 'AAVE-PERP',
    params= params,
    ohlcvs = ohlcvs,
    timeFrames= [timeframe],
    tradeLogs = False
)

rsiStrat.run()

results = rsiStrat.calcResults()
rsiStrat.showResults(results)