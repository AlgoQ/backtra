import numpy as np
import pandas as pd
from talib import ATR
import quantstats as qs

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
    
    def openTrade(self, id, time, side, tradeType, leverage, amount, openPrice, **kwargs):
        self.openTradesL[id] = {'openTime': time, 'side': side, 'leverage': leverage, 'amount': amount * (1 - self.reduceAmount) * leverage, 'openPrice': openPrice, 'profitReal': 0}

        if tradeType == 'limit':
            feeRate = self.makerFee
        elif tradeType == 'market':
            feeRate = self.takerFee
        
        self.openTradesL[id]['feesProc'] = feeRate
        self.openTradesL[id]['fees'] = self.openTradesL[id]['amount'] * feeRate

        for key, value in kwargs.items():
            self.openTradesL[id][key] = value

        if self.tradeLogs == True:
            print(f'{time} - {side.capitalize()} trade is been opened at {round(openPrice, self.ohlcvs["precision"])}, with {round(amount, self.ohlcvs["precision"])} as amount')

    def closeTrade(self, id, time, tradeType, closePrice, quantity=1, ema=None):
        self.openTradesL[id]['closeTime'] = time
        self.openTradesL[id]['closePrice'] = closePrice

        closeAmount = self.openTradesL[id]['amount'] * quantity
        
        if tradeType in ['limit', 'stopLimit']:
            feeRate = self.makerFee
        elif tradeType in ['market', 'stopMarket']:
            feeRate = self.takerFee
        
        self.openTradesL[id]['feesProc'] += feeRate
        self.openTradesL[id]['fees'] += closeAmount * feeRate

        if self.openTradesL[id]['side'] == 'long':
            profitProc = (closePrice - self.openTradesL[id]['openPrice']) / self.openTradesL[id]['openPrice'] * quantity + (self.openTradesL[id]['feesProc'] * self.openTradesL[id]['leverage'] * quantity)
            self.openTradesL[id]['profitProc'] = profitProc
        elif self.openTradesL[id]['side'] == 'short':
            profitProc = (self.openTradesL[id]['openPrice'] - closePrice) / self.openTradesL[id]['openPrice'] * quantity + (self.openTradesL[id]['feesProc'] * self.openTradesL[id]['leverage'] * quantity)
            self.openTradesL[id]['profitProc'] = profitProc
            
        self.openTradesL[id]['profitReal'] += round(profitProc * closeAmount, 8)
        
        self.capital += self.openTradesL[id]['profitReal']
        self.capital = round(self.capital, 8)
        self.capitalFollowup.append([time , self.capital])

        if self.tradeLogs == True:
            if quantity < 1:
                print(f'{time} - {self.openTradesL[id]["side"].capitalize()} trade is been partly closed at {round(closePrice, self.ohlcvs["precision"])}, profit/loss: {round(self.openTradesL[id]["profitReal"], 4)} and current capital is now {self.capital}')
            else:
                print(f'{time} - {self.openTradesL[id]["side"].capitalize()} trade is been closed at {round(closePrice, self.ohlcvs["precision"])}, profit/loss: {round(self.openTradesL[id]["profitReal"], 4)} and current capital is now {self.capital}')
        
        self.openTradesL[id]['amount'] = self.openTradesL[id]['amount'] - closeAmount

        if quantity == 1:
            self.closedTradesL.append(self.openTradesL[id])
            self.openTradesL.pop(id)

    def calcResults(self):
        # print(self.capitalFollowup)
        
        # Do necassary calculations
        capitalList = []
        for i in self.capitalFollowup:
            capitalList.append(i[-1])

        drawdownL = []

        indexCap = 0
        
        for i in capitalList:
            prevIndex = indexCap - 1
            if i < capitalList[prevIndex] and indexCap > 0:
                drawdown = (i - max(capitalList[:prevIndex + 1])) / max(capitalList[:prevIndex + 1])
                drawdownL.append(drawdown)

            indexCap += 1

        winningTrades = []
        losingTrades = []
        longTrades = []
        shortTrades = []
        for closedTrade in self.closedTradesL:
            if closedTrade['profitProc'] >= 0:
                winningTrades.append(closedTrade['profitProc'])
            else:
                losingTrades.append(closedTrade['profitProc'])
            
            if closedTrade['side'] == 'long':
                longTrades.append(closedTrade['profitProc'])
            else:
                shortTrades.append(closedTrade['profitProc'])
        
        if len(drawdownL) > 0:
            if len(shortTrades) > 0:
                results = {
                    'Strategy': self.strategyName,
                    'Symbol': self.symbol,
                    'Timeframes': self.timeFrames,
                    'Parameters': self.params,
                    'Start': self.ohlcvs[self.timeFrames[0]].index[1],
                    'End': self.ohlcvs[self.timeFrames[0]].index[-1],
                    'Duration (days)': abs((self.ohlcvs[self.timeFrames[0]].index[-1] - self.ohlcvs[self.timeFrames[0]].index[1]).days),
                    'Equity Start [$]': round(capitalList[0], 4),
                    'Equity Final [$]': round(capitalList[-1], 4),
                    'Equity Max [$]': round(max(capitalList), 4),
                    'Return [%]': round((capitalList[-1] - capitalList[0]) / capitalList[0] * 100, 2),
                    'Max. Drawdown [%]': round(min(drawdownL) * 100, 2),
                    'Win rate [%]': round(len(winningTrades)/len(self.closedTradesL) * 100, 2),
                    'Buy & Hold [%]': round((self.ohlcvs[self.timeFrames[0]]['close'][-1] - self.ohlcvs[self.timeFrames[0]]['close'][0]) / self.ohlcvs[self.timeFrames[0]]['close'][0] * 100, 2),
                    'Total trades': len(self.closedTradesL),
                    'Avg. trade [%]': round(sum(winningTrades + losingTrades) / len(winningTrades + losingTrades) * 100, 2),
                    'Avg. winning trade [%]': round(sum(winningTrades) / len(winningTrades) * 100, 2),
                    'Avg. losing trade [%]': round(sum(losingTrades) / len(losingTrades) * 100, 2),
                    'Avg. long trade [%]': round(sum(longTrades) / len(longTrades) * 100, 2),
                    'Avg. short trade [%]': round(sum(shortTrades) / len(shortTrades) * 100, 2)
                }
            else:
                results = {
                    'Strategy': self.strategyName,
                    'Symbol': self.symbol,
                    'Timeframes': self.timeFrames,
                    'Parameters': self.params,
                    'Start': self.ohlcvs[self.timeFrames[0]].index[1],
                    'End': self.ohlcvs[self.timeFrames[0]].index[-1],
                    'Duration (days)': abs((self.ohlcvs[self.timeFrames[0]].index[-1] - self.ohlcvs[self.timeFrames[0]].index[1]).days),
                    'Equity Start [$]': round(capitalList[0], 4),
                    'Equity Final [$]': round(capitalList[-1], 4),
                    'Equity Max [$]': round(max(capitalList), 4),
                    'Return [%]': round((capitalList[-1] - capitalList[0]) / capitalList[0] * 100, 2),
                    'Max. Drawdown [%]': round(min(drawdownL) * 100, 2),
                    'Win rate [%]': round(len(winningTrades)/len(self.closedTradesL) * 100, 2),
                    'Buy & Hold [%]': round((self.ohlcvs[self.timeFrames[0]]['close'][-1] - self.ohlcvs[self.timeFrames[0]]['close'][0]) / self.ohlcvs[self.timeFrames[0]]['close'][0] * 100, 2),
                    'Total trades': len(self.closedTradesL),
                    'Avg. trade [%]': round(sum(winningTrades + losingTrades) / len(winningTrades + losingTrades) * 100, 2),
                    'Avg. winning trade [%]': round(sum(winningTrades) / len(winningTrades) * 100, 2),
                    'Avg. losing trade [%]': round(sum(losingTrades) / len(losingTrades) * 100, 2),
                    'Avg. long trade [%]': round(sum(longTrades) / len(longTrades) * 100, 2)
                }
            
            percChange = pd.DataFrame(self.capitalFollowup, columns=['Date', 'Perc'])
            percChange = percChange.set_index(['Date'])
            percChange.index = pd.to_datetime(percChange.index)
            percChange = percChange.squeeze().pct_change()

            return [results, percChange]
        else:
            return None
    
    def showResults(self, results):
        keys = list(results.keys())

        keysLen = []

        for key in keys:
            keysLen.append(len(key))

        maxLen = max(keysLen) + 1

        print('\n')
        for key, value in results.items():
            print(f'{key}{" " * (maxLen - len(key))}{value}')

    def calcAtr(self, tempDf, longOrShort, atrPeriod:int = 14):
        warnings.filterwarnings("ignore")
        tempDf2 = self.histTrades.loc[str(tempDf.index[-1]):str(tempDf.index[-1] + datetime.timedelta(minutes=5))]
        
        try:
            if longOrShort == 'l':
                mask = (tempDf2.index > str(tempDf.index[-1])) & (tempDf2.index <= str(tempDf2[tempDf2['price'].ge(tempDf['close'][-1])].index[id]))
            else:
                mask = (tempDf2.index > str(tempDf.index[-1])) & (tempDf2.index <= str(tempDf2[tempDf2['price'].le(tempDf['close'][-1])].index[id]))

            atrRow = tempDf2.loc[mask].groupby(pd.Grouper(freq='5T')).agg({'price': ['first', max, min, 'last'], 'amount': sum}) # TODO: Change Timeframe
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