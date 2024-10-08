from flask import Flask, request, render_template, jsonify
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import csv
from flask_cors import CORS

# Initialize Flask App

app = Flask(__name__)

# Dynamically set Access-Control-Allow-Origin based on request origin
@app.after_request
def apply_cors(response):
    # Extract origin from request headers
    origin = request.headers.get('Origin')
    allowed_origins = ['http://localhost:8000', 'http://localhost:5173']
    
    # Check if the request's origin is in the allowed list
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
    
    return response

CORS(app)

def fetch_yahoo_data(ticker, interval, ema_period=20, rsi_period=14):
    end_date = datetime.now()
    if interval in ['1m', '5m']:
        start_date = end_date - timedelta(days=7)
    elif interval in ['15m', '60m']:
        start_date = end_date - timedelta(days=60)
    elif interval == '1d':
        start_date = end_date - timedelta(days=365*5)
    elif interval == '1wk':
        start_date = end_date - timedelta(weeks=365*5)
    elif interval == '1mo':
        start_date = end_date - timedelta(days=365*5)

    data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
    data['EMA'] = ta.ema(data['Close'], length=ema_period)
    data['RSI'] = ta.rsi(data['Close'], length=rsi_period)

    candlestick_data = [
        {
            'time': int(row.Index.timestamp()),
            'open': row.Open,
            'high': row.High,
            'low': row.Low,
            'close': row.Close
        }
        for row in data.itertuples()
    ]

    ema_data = [
        {
            'time': int(row.Index.timestamp()),
            'value': row.EMA
        }
        for row in data.itertuples() if not pd.isna(row.EMA)
    ]

    rsi_data = [
        {
            'time': int(row.Index.timestamp()),
            'value': row.RSI if not pd.isna(row.RSI) else 0  # Convert NaN to zero
        }
        for row in data.itertuples()
    ]

    return candlestick_data, ema_data, rsi_data
def load_stocks():
    stocks = []
    with open('stocks.csv', mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            stocks.append({
                'symbol': row['symbol'],
                'company_name': row['company_name']
            })
    return stocks

@app.route('/api/search')
def search_stocks():
    query = request.args.get('q', '').lower()
    stocks = load_stocks()
    filtered_stocks = [stock for stock in stocks if query in stock['symbol'].lower() or query in stock['company_name'].lower()]
    return jsonify(filtered_stocks)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data/<ticker>/<interval>/<int:ema_period>/<int:rsi_period>')
def get_data(ticker, interval, ema_period, rsi_period):
    candlestick_data, ema_data, rsi_data = fetch_yahoo_data(ticker, interval, ema_period, rsi_period)
    return jsonify({'candlestick': candlestick_data, 'ema': ema_data, 'rsi': rsi_data})

@app.route('/api/symbols')
def get_symbols():
    with open('symbols.txt') as f:
        symbols = [line.strip() for line in f]
    return jsonify(symbols)

@app.route('/api/<symbol>', methods=['GET'])
def get_stock_price(symbol):
    if not symbol:
        return jsonify({'error': 'No stock symbol provided'}), 400
    
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history()
        market_price = data['Close'].iloc[-1]
        market_price = round(market_price, 2)
        return jsonify({'symbol': symbol, 'market_price': market_price})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/info/<symbol>', methods=['GET'])
def company(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.info.get('longName', 'NaN')


if __name__ == '__main__':
    app.run(debug=True)