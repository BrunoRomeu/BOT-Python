
from binance.client import Client 
from binance import Client
from secrets import api_key, api_secret
from binance.enums import *

import pandas as pd
import numpy as np
import ta
import time

client = Client(api_key, api_secret)

def getminutedata(symbol, interval, lookback):
	frame = pd.DataFrame(client.get_historical_klines(symbol, interval, lookback + ' min ago UTC'))
	frame = frame.iloc[:,:6]
	frame.columns = ['time','Open','High','Low','Close','Volume']
	frame = frame.set_index('time')
	frame.index = pd.to_datetime(frame.index, unit = 'ms')
	frame = frame.astype(float)
	return frame

df = getminutedata('ADAUSDT', '1m', '100')

#Aqui é possivel ver a cotação da moeda em tempo real
#print(df)

def applytechnicals(df):
	df['%K'] = ta.momentum.stoch(df.High,df.Low ,df.Close, window = 8, smooth_window = 3)
	df['%D'] = df['%K'].rolling(3).mean()
	df['rsi'] = ta.momentum.rsi(df.Close, window = 16)
	df['macd'] = ta.trend.macd_diff(df.Close)
	df.dropna(inplace=True)

applytechnicals(df)
#Aqui é possivel ver os indicadores em tempo real
#print(df)

class Signals:
	def __init__(self, df, lags):
		self.df = df
		self.lags = lags

	def gettriggers(self):
		dfx = pd.DataFrame()
		for i in range(self.lags +1):
			mask = (self.df['%K'].shift(i) < 20) & (self.df['%D'].shift(i) < 20)
			dfxn = pd.DataFrame([mask] )
			dfx = pd.concat([dfx, dfxn])
	def decide(self):
		self.df['trigger'] = np.where(self.gettriggers(), 1, 0)
		self.df['Buy'] = np.where((self.df.trigger) & (self.df['%K'].between(20,80)) & 
		(self.df['%D'].between(20,80)) & 
		(self.df.rsi > 40) & (self.df.macd > 0),1,0)

#Aqui é possivel ver todos os sinais de compra pelos indicadores, o valor final mostra as colunas (25):
inst = Signals(df, 25)
inst.decide()
#Mostrar a tabela:
#print([df.Buy == 1])

def strategy(pair, qty, open_position = False):
	df = getminutedata(pair, '1m', '100')
	applytechnicals(df)
	inst = Signals(df, 25)
	inst.decide()
	print(f'current Close is ' + str(df.Close.iloc[-1]))
	if df.Buy.iloc[-1]:
		order = client.creat_order(symbol = pair, side = 'BUY', type = 'MARKET', quantity = qty)
		print(order)
		buyprice = float(order['fills'][0]['price'])	
		open_position = True
	while open_position:
		time.sleep(0.5)
		df = getminutedata(pair, '1m', '2')
		print(f'currtent Close ' + str(df.Close.iloc[-1]))
		print(f'current Target ' + str(buyprice * 1.005))
		print(f'current Stop is ' + str(buyprice * 0.995))
		if df.Close[-1] <= buyprice * 0.995 or df.Close[-1] >= 1.005 * buyprice:
			order = client.creat_order(symbol = pair, side = 'SELL', type = 'MARKET', quantity = qty)
			print(order)		
			break
					
while True:
	strategy('ADAUSDT', 10)
	time.sleep(0.5)
