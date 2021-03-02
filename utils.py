import glob
import numpy as np
import pandas as pd

def fetchFolder(folderPath):
    print('Loading files...')
    all_files = glob.glob(folderPath + '/*.csv')

    li = []

    for filename in all_files:
        df = pd.read_csv(filename, index_col=None, header=0)
        li.append(df)
    
    histTrades = pd.concat(li, axis=0, ignore_index=True)
    histTrades = histTrades.set_index('date')
    histTrades.index = pd.to_datetime(histTrades.index, unit='ms')

    return histTrades

def fetchFile(filePath):
    histTrades = pd.read_csv(filePath, index_col=None, header=0)
    histTrades = histTrades.set_index('date')
    histTrades.index = pd.to_datetime(histTrades.index, unit='ms')

    return histTrades

def jsonToOhlcv(jsonFilename, interval):
    ohlcv = pd.read_json(jsonFilename)
    ohlcv.columns = ['date', 'open', 'high', 'low', 'close', 'volume']

    ohlcv = ohlcv.set_index('date')
    ohlcv.index = pd.to_datetime(ohlcv.index, unit='ms')

    ohlcv = ohlcv.groupby(pd.Grouper(freq=interval)).agg({'open': 'first', 'high': max, 'low': min, 'close': 'last', 'volume': sum})

    return ohlcv.dropna()