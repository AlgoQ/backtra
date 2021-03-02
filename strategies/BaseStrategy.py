import numpy as np
import pandas as pd
from talib import ATR

import datetime
import json
import warnings

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# !!!!! DON'T CHANGE THIS FILE !!!!!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

class BaseStrategy():
    def _calcMinKlines(self):
        paramsList = []

        for paramName, value in self.params.items():
            if isinstance(value, int):
                paramsList.append(value)
            elif isinstance(value, dict):
                for paramName, value in value.items():
                    paramsList.append(value)

        return max(paramsList) + 1
    
    def _getConfigData(self):
        with open('./config.json') as f:
            configData = json.load(f)

        return configData
    
    def _createOhlcvs(self):
        ohlcvs = {}
        for interval in self.timeFrames:
            ohlcv = self.histTrades.groupby(pd.Grouper(freq=interval)).agg({'price': ['first', max, min, 'last'], 'amount': sum})

            ohlcv.columns = ['open', 'high', 'low', 'close', 'volume']

            precision = ohlcv['close'].apply(lambda x: len(str(x).split('.')[-1])).max()

            pip = float('0.' + ('0' * (precision - 1)) + '1')

            ohlcvs['precision'] = precision
            ohlcvs['pip'] = pip
            ohlcvs[interval] = ohlcv

        return ohlcvs

    def currentTimeUTC(self):
        return datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    def run(self):
        # Override this function
        pass
    
    def openTrade(self, time, side, tradeType, leverage, amount, openPrice, **kwargs):
        self.openTradesL.append({'openTime': time, 'side': side, 'leverage': leverage, 'amount': amount, 'openPrice': openPrice})

        if tradeType == 'limit':
            self.openTradesL[0]['feeProc'] = self.makerFee
            self.openTradesL[0]['fee'] = amount * (1 - self.reduceAmount) * leverage * (self.makerFee * self.leverage)
        elif tradeType == 'market':
            self.openTradesL[0]['feeProc'] = self.takerFee
            self.openTradesL[0]['fee'] = amount * (1 - self.reduceAmount) * leverage * (self.takerFee * self.leverage)

        for key, value in kwargs.items():
            self.openTradesL[0][key] = value

        if self.tradeLogs == True:
            print(f'{time} - {side.capitalize()} trade is been opened at {openPrice}, with {amount} amount and {leverage} leverage')

    def closeTrade(self, time, tradeType, closePrice):
        self.openTradesL[0]['closeTime'] = time
        self.openTradesL[0]['closePrice'] = closePrice

        if tradeType in ['limit', 'stopLimit']:
            self.openTradesL[0]['feeProc'] += self.makerFee
            self.openTradesL[0]['fee'] += self.openTradesL[0]['amount'] * (1 - self.reduceAmount) * self.openTradesL[0]['leverage'] * self.makerFee
        elif tradeType == ['market', 'stopMarket']:
            self.openTradesL[0]['feeProc'] += self.takerFee
            self.openTradesL[0]['fee'] += self.openTradesL[0]['amount'] * (1 - self.reduceAmount) * self.openTradesL[0]['leverage'] * self.takerFee

        if self.openTradesL[0]['side'] == 'long':
            self.openTradesL[0]['profitProc'] = (closePrice - self.openTradesL[0]['openPrice']) / self.openTradesL[0]['openPrice']
        elif self.openTradesL[0]['side'] == 'short':
            self.openTradesL[0]['profitProc'] = (self.openTradesL[0]['openPrice'] - closePrice) / self.openTradesL[0]['openPrice']
            
        self.openTradesL[0]['profitReal'] = round(self.openTradesL[0]['profitProc'] * self.openTradesL[0]['amount'] * (1 - self.reduceAmount) * self.openTradesL[0]['leverage'] + self.openTradesL[0]['fee'], 4)
        
        self.capital += self.openTradesL[0]['profitReal']
        self.capital = round(self.capital, 4)
        self.capitalFollowup.append(self.capital)

        if self.tradeLogs == True:
            print(f'{time} - {self.openTradesL[0]["side"].capitalize()} trade is been closed at {closePrice}, profit/loss: {self.openTradesL[0]["profitReal"]} and current capital is now {self.capital}')

        self.closedTradesL.append(self.openTradesL[0])
        self.openTradesL.pop()

    def calcResults(self):
        indexMaxEquity = self.capitalFollowup.index(max(self.capitalFollowup))
        drawdownL = []

        indexCap = 0
        
        for i in self.capitalFollowup:
            prevIndex = indexCap - 1
            if i < self.capitalFollowup[prevIndex] and indexCap > 0:
                drawdown = (i - max(self.capitalFollowup[:prevIndex + 1])) / max(self.capitalFollowup[:prevIndex + 1])
                drawdownL.append(drawdown)

            indexCap += 1

        winningTrades = []
        losingTrades = []
        for closedTrade in self.closedTradesL:
            if closedTrade['profitProc'] >= 0:
                winningTrades.append(closedTrade['profitProc'])
            else:
                losingTrades.append(closedTrade['profitProc'])
        
        results = {
            'Strategy': self.strategyName,
            'Symbol': self.symbol,
            'Timeframes': self.timeFrames,
            'Parameters': self.params,
            'Start': self.ohlcvs[self.timeFrames[0]].index[1],
            'End': self.ohlcvs[self.timeFrames[0]].index[-1],
            'Duration': abs((self.ohlcvs[self.timeFrames[0]].index[-1] - self.ohlcvs[self.timeFrames[0]].index[1]).days),
            'Equity Start [$]': self.capitalFollowup[0],
            'Equity Final [$]': round(self.capitalFollowup[-1], 4),
            'Return [%]': round((self.capitalFollowup[-1] - self.capitalFollowup[0]) / self.capitalFollowup[0] * 100, 2),
            'Max. Drawdown [%]': round(min(drawdownL) * 100, 2),
            'Win rate [%]': round(len(winningTrades)/len(self.closedTradesL) * 100, 2),
            'Total trades': len(self.closedTradesL),
            'Avg. trade [%]': round(sum(winningTrades + losingTrades) / len(winningTrades + losingTrades) * 100, 2),
            'Avg. winning trade [%]': round(sum(winningTrades) / len(winningTrades) * 100, 2),
            'Avg. losing trade [%]': round(sum(losingTrades) / len(losingTrades) * 100, 2)
        }
    
    def showResults(self, results):
        keys = list(results.keys())
        maxLen = max(keys, key=len) + 1

        for key, value in results.items():
            print(f'{key}{" " * (maxLen - len(key))}{value}')

    def calcAtr(self, tempDf, longOrShort, atrPeriod:int = 14):
        warnings.filterwarnings("ignore")
        tempDf2 = self.histTrades.loc[str(tempDf.index[-1]):str(tempDf.index[-1] + datetime.timedelta(minutes=5))]
        
        try:
            if longOrShort == 'l':
                mask = (tempDf2.index > str(tempDf.index[-1])) & (tempDf2.index <= str(tempDf2[tempDf2['price'].ge(tempDf['close'][-1])].index[0]))
            else:
                mask = (tempDf2.index > str(tempDf.index[-1])) & (tempDf2.index <= str(tempDf2[tempDf2['price'].le(tempDf['close'][-1])].index[0]))

            atrRow = tempDf2.loc[mask].groupby(pd.Grouper(freq='5T')).agg({'price': ['first', max, min, 'last'], 'amount': sum}) # TODO: Timeframe aanpassen
            atrRow.columns = ['open', 'high', 'low', 'close', 'volume']

            atrDf = pd.concat([tempDf[:-1].copy(), atrRow])
        
        except IndexError:
            atrDf = tempDf.copy()

        atr = ATR(atrDf['high'], atrDf['low'], atrDf['close'], atrPeriod)

        return atr
    
    def calcLeverage(self, atr, openPrice, slMultipier, maxLossPerc):
        leverage = round(1 / (atr[-1] * slMultipier / openPrice)) / 100 * maxLossPerc
        
        if leverage == 0:
            leverage = 1

        return round(leverage)