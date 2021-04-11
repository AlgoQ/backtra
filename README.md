# Backtra

Backtra is an advanced futures backtesting framework where we loop through kline (ohlcv) data on a specific way to acheive more realistic results.

This is a futures backtesting framework but it can also be used for spot backtesting.

**More in-depth documentation is coming soon!**

## Getting Started
We will be backtesting a simple golden cross strategy with a stoploss and take profit based on the ATR. The leverage is also based on the ATR and the max percentage you are willing to lose per trade.

![Golden Cross](https://www.investopedia.com/thmb/NXwxIinKHx9FmoP52xsMkae6lbs=/1536x0/filters:no_upscale():max_bytes(150000):strip_icc():format(webp)/GoldenCross-5c6592b646e0fb0001a91e29.png)

1. **Config**

Rename the `exampleConfig.json` file to `config.json` and update the parameters if wanted.

```json
{
    "capital": 10000,
    "makerFee": -0.0025,
    "takerFee": 0.0075,
    "reduceAmount": 0
}
```


2. **Strategy**

Create a strategy named `GoldenCross.py` and add it into the strategies folder.

More info about creating a strategy will be added *soon*.

```python
from strategies.BaseStrategy import BaseStrategy

import numpy as np
import pandas as pd

# TODO: Import needed indicators
from talib import SMA, ATR

class GoldenCross(BaseStrategy):
    def __init__(self, strategyName, symbol, params, timeFrames, ohlcvs, tradeLogs=True):
        # Changeable values
        self.strategyName = strategyName
        self.symbol       = symbol
        self.params       = params
        self.timeFrames   = timeFrames
        self.ohlcvs       = ohlcvs
        self.tradeLogs    = tradeLogs
        
        # Fixed values
        self.configData      = self._getConfigData()
        self.capital         = self.configData['capital']
        self.makerFee        = self.configData['makerFee']
        self.takerFee        = self.configData['takerFee']
        self.reduceAmount    = self.configData['reduceAmount']
        self.capitalFollowup = [self.capital]
        self.openTradesL     = []
        self.closedTradesL   = []
    
    def run(self):
        print('Trading started...')
        minKlines = max(200, self._calcMinKlines())
        
        for i in range(minKlines, len(self.ohlcvs[self.timeFrames[0]])): # TODO: Chance to timeframe you want to use (also on line below this)
            tempDf = self.ohlcvs[self.timeFrames[0]].iloc[i-minKlines:i+1].copy()
        
            if len(self.openTradesL) == 0:
                # Indicators
                sma1 = SMA(tempDf['close'], self.params['sma1'])
                sma2 = SMA(tempDf['close'], self.params['sma2'])

                if sma1[-2] < sma2[-2]: # Long condition 1
                    tempDf.loc[tempDf.index[-1], 'close'] = tempDf['high'][-1]
                    sma1 = SMA(tempDf['close'], self.params['sma1'])
                    sma2 = SMA(tempDf['close'], self.params['sma2'])
                    
                    if sma1[-1] > sma2[-1]: # Long condition 2
                        for i in np.arange(tempDf['open'][-1], tempDf['high'][-1] + self.ohlcvs['pip'], self.ohlcvs['pip']):
                            openPrice = round(i, self.ohlcvs['precision'])
                            tempDf.loc[tempDf.index[-1], 'close'] = openPrice

                            # Indicators
                            sma1 = SMA(tempDf['close'], self.params['sma1'])
                            sma2 = SMA(tempDf['close'], self.params['sma2'])

                            if sma1[-1] > sma2[-1]: # Long condition 2
                                atr = ATR(tempDf['high'], tempDf['low'], tempDf['close'], self.params['atr'])
                                # Calculate leverage based on atr and max percentage you are willing to lose per trade
                                leverage = self.calcLeverage(atr=atr, openPrice=openPrice, slMultipier=self.params['slMultipier'], maxLossPerc=self.params['maxLossPerc'])

                                self.openTrade(time=tempDf.index[-1], side='long', tradeType='market', leverage=self.params['leverage'], amount=self.capital, openPrice=openPrice, slPrice=round(openPrice - atr[-1] * self.params['slMultipier'], self.ohlcvs['precision']), tpPrice=round(openPrice + atr[-1] * self.params['tpMultipier'], self.ohlcvs['precision']))
                                break
                
                elif sma1[-2] > sma2[-2]: # Short condition 1
                    tempDf.loc[tempDf.index[-1], 'close'] = tempDf['low'][-1]
                    sma1 = SMA(tempDf['close'], self.params['sma1'])
                    sma2 = SMA(tempDf['close'], self.params['sma2'])
                    
                    if sma1[-1] < sma2[-1]: # Short condition 2
                        for i in np.arange(tempDf['open'][-1], tempDf['low'][-1] - self.ohlcvs['pip'], self.ohlcvs['pip'] * -1):
                            openPrice = round(i, self.ohlcvs['precision'])
                            tempDf.loc[tempDf.index[-1], 'close'] = openPrice
                            
                            # Indicators
                            sma1 = SMA(tempDf['close'], self.params['sma1'])
                            sma2 = SMA(tempDf['close'], self.params['sma2'])

                            if sma1[-1] < sma2[-1]: # Short condition 2
                                atr = ATR(tempDf['high'], tempDf['low'], tempDf['close'], self.params['atr'])
                                # Calculate leverage based on atr and max percentage you are willing to lose per trade
                                leverage = self.calcLeverage(atr=atr, openPrice=openPrice, slMultipier=self.params['slMultipier'], maxLossPerc=self.params['maxLossPerc'])

                                self.openTrade(time=tempDf.index[-1], side='short', tradeType='market', leverage=self.params['leverage'], amount=self.capital, openPrice=openPrice, slPrice=round(openPrice + atr[-1] * self.params['slMultipier'], self.ohlcvs['precision']), tpPrice=round(openPrice - atr[-1] * self.params['tpMultipier'], self.ohlcvs['precision']))
                                break

            if len(self.openTradesL) > 0:
                if self.openTradesL[0]['side'] == 'long':
                    if tempDf['low'][-1] < self.openTradesL[0]['slPrice']:
                        self.closeTrade(time=tempDf.index[-1], tradeType='market', closePrice=self.openTradesL[0]['slPrice'])
                    elif tempDf['high'][-1] > self.openTradesL[0]['tpPrice']:
                        self.closeTrade(time=tempDf.index[-1], tradeType='market', closePrice=self.openTradesL[0]['tpPrice'])
                
                elif self.openTradesL[0]['side'] == 'short':
                    if tempDf['high'][-1] > self.openTradesL[0]['slPrice']:
                        self.closeTrade(time=tempDf.index[-1], tradeType='market', closePrice=self.openTradesL[0]['slPrice'])
                    elif tempDf['low'][-1] < self.openTradesL[0]['tpPrice']:
                        self.closeTrade(time=tempDf.index[-1], tradeType='market', closePrice=self.openTradesL[0]['tpPrice'])
```


3. **Main File**

Now we will create a main file that connects/runs our strategy.
I this file we send all variable values through the params, select timeframe and link your data.
Create `mainGoldenCross.py` in the main folder:

```python
from strategies.GoldenCross2 import GoldenCross
from utils import jsonToOhlcv

# Include all variable values in the params
params = {'sma1': 50, 'sma2': 200, 'atr': 14, 'tpMultipier': 2, 'slMultipier': 5, 'maxLossPerc': 2, 'leverage': 2}
timeframe = '30T'

# Convert json data file to 30min ohlcv dataframe
ohlcv = jsonToOhlcv(r'data/ohlcv_ftx_AAVEPERP_179days.json', timeframe)

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
```

If you don't have any ohlcv/kline data you can always fetch crypto kline data with [FEDA](https://github.com/JanssensKobe/feda).

## Upcoming
* More in-depth documentation
* Slippage parameter in the config
* Optimization