from strategies.BaseStrategy import BaseStrategy

import numpy as np
import pandas as pd

# TODO: Import needed indicators
from talib import RSI

# Simple RSI Strategy where we go long when the price crosses over the value 50 and visa verca

class RsiStrategy(BaseStrategy):
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
        minKlines = max(200, self._calcMinKlines())

        for i in range(minKlines, len(self.ohlcvs[self.timeFrames[0]])):
            tempDf = self.ohlcvs[self.timeFrames[0]].iloc[i-minKlines:i+1].copy()

            rsi = RSI(tempDf['close'], self.params['rsi'])
        
            if rsi[-2] < 50: # Long condition 1
                tempDf.loc[tempDf.index[-1], 'close'] = tempDf['high'][-1]
                rsi = RSI(tempDf['close'], self.params['rsi'])

                if rsi[-1] > 50: # Long condition 2
                    for i in np.arange(tempDf['open'][-1], tempDf['high'][-1] + self.ohlcvs['pip'], self.ohlcvs['pip']):
                        openPrice = round(i, self.ohlcvs['precision'])
                        tempDf.loc[tempDf.index[-1], 'close'] = openPrice

                        # Indicators
                        rsi = RSI(tempDf['close'], self.params['rsi'])

                        if rsi[-1] > 50: # Long condition 2
                            if len(self.openTradesL) > 0:
                                self.closeTrade(time=tempDf.index[-1], tradeType='market', closePrice=openPrice)
                            
                            self.openTrade(time=tempDf.index[-1], side='long', tradeType='market', leverage=self.params['leverage'], amount=self.capital, openPrice=openPrice)
                            break
            
            elif rsi[-2] > 50: # Short condition 1
                tempDf.loc[tempDf.index[-1], 'close'] = tempDf['low'][-1]
                rsi = RSI(tempDf['close'], self.params['rsi'])

                if rsi[-1] < 50: # Short condition 2
                    for i in np.arange(tempDf['open'][-1], tempDf['low'][-1] - self.ohlcvs['pip'], self.ohlcvs['pip'] * -1):
                        openPrice = round(i, self.ohlcvs['precision'])
                        tempDf.loc[tempDf.index[-1], 'close'] = openPrice

                        # Indicators
                        rsi = RSI(tempDf['close'], self.params['rsi'])

                        if rsi[-1] < 50: # Short condition 2
                            if len(self.openTradesL) > 0:
                                self.closeTrade(time=tempDf.index[-1], tradeType='market', closePrice=openPrice)

                            self.openTrade(time=tempDf.index[-1], side='short', tradeType='market', leverage=self.params['leverage'], amount=self.capital, openPrice=openPrice)
                            break