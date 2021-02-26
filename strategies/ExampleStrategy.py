from strategies.BaseStrategy import BaseStrategy

from talib import SMA, ATR
import numpy as np
import pandas as pd

class ExampleStrategy(BaseStrategy):
    def __init__(self, strategyName, symbol, params, histTrades, timeFrames, tpMultipier, slMultipier, maxLossPerc, leverage):
        # Changeable values
        self.strategyName = strategyName
        self.symbol       = symbol
        self.params       = params
        self.histTrades   = histTrades
        self.timeFrames   = timeFrames
        self.leverage     = leverage
        
        # Fixed values
        self.configData      = self._getConfigData()
        self.capital         = self.configData['capital']
        self.makerFee        = self.configData['makerFee']
        self.takerFee        = self.configData['takerFee']
        self.reduceAmount    = self.configData['reduceAmount']
        self.ohlcvs          = self._createOhlcvs()
        self.capitalFollowup = [self.capital]
        self.openTradesL     = []
        self.closedTradesL   = []
        self.tradeLogs       = True
        
        # Optional
        self.tpMultipier = tpMultipier
        self.slMultipier = slMultipier
        self.maxLossPerc = maxLossPerc
    
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
                                atr = self.calcAtr(tempDf=tempDf, longOrShort='l', atrPeriod=self.params['atr'])
                                leverage = self.calcLeverage(atr=atr, openPrice=openPrice, slMultipier=self.slMultipier, maxLossPerc=self.maxLossPerc)

                                self.openTrade(time=tempDf.index[-1], side='long', tradeType='market', leverage=leverage, amount=self.capital, openPrice=openPrice, slPrice=round(openPrice - atr[-1] * self.slMultipier, self.ohlcvs['precision']), tpPrice=round(openPrice + atr[-1] * self.tpMultipier, self.ohlcvs['precision']))
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
                                atr = self.calcAtr(tempDf=tempDf, longOrShort='s', atrPeriod=self.params['atr'])
                                leverage = self.calcLeverage(atr=atr, openPrice=openPrice, slMultipier=self.slMultipier, maxLossPerc=self.maxLossPerc)

                                self.openTrade(time=tempDf.index[-1], side='short', tradeType='market', leverage=leverage, amount=self.capital, openPrice=openPrice, slPrice=round(openPrice + atr[-1] * self.slMultipier, self.ohlcvs['precision']), tpPrice=round(openPrice - atr[-1] * self.tpMultipier, self.ohlcvs['precision']))
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