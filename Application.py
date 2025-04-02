from flask import Flask, render_template, request, jsonify
import pymysql
import yfinance as yf

app = Flask(__name__)
db_config = {
    "host": "localhost",
    "user": "root",  # Change as needed
    "password": "Rajan@12/11/98",  # Change as needed
    "database": "algo",
    "port": 3306
}

def create_tables():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data (
            datetime DATETIME PRIMARY KEY,
            open FLOAT, high FLOAT, low FLOAT, close FLOAT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            datetime DATETIME PRIMARY KEY,
            upper FLOAT, lower FLOAT, sma FLOAT
        )
    """)
    
    conn.commit()
    conn.close()

def fetch_and_store_nifty_data():
    ticker = "^NSEI"
    data = yf.download(ticker, period="1y", interval="1d", auto_adjust=True)
    
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    for date, row in data.iterrows():
        datetime_str = date.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT IGNORE INTO data (datetime, open, high, low, close) 
            VALUES (%s, %s, %s, %s, %s)
        """, (datetime_str, row["Open"], row["High"], row["Low"], row["Close"]))
    
    conn.commit()
    conn.close()

def calculate_and_store_bollinger_bands():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    cursor.execute("SELECT datetime, close FROM data ORDER BY datetime ASC")
    data = cursor.fetchall()  # Fetch all rows

    if len(data) < 20:
        print("Not enough data to calculate Bollinger Bands.")
        conn.close()
        return

    closes = [row[1] for row in data]
    datetimes = [row[0] for row in data]

    window = 20
    for i in range(window - 1, len(closes)):
        subset = closes[i - window + 1: i + 1]
        sma = sum(subset) / window
        std_dev = (sum([(x - sma) ** 2 for x in subset]) / window) ** 0.5
        upper_band = sma + (2 * std_dev)
        lower_band = sma - (2 * std_dev)

        cursor.execute("""
            INSERT IGNORE INTO indicators (datetime, upper, lower, sma)
            VALUES (%s, %s, %s, %s)
        """, (datetimes[i], upper_band, lower_band, sma))

    conn.commit()
    conn.close()
    print("Bollinger Bands calculated and stored successfully!")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_data', methods=['POST'])
def fetch_data():
    date = request.form['date']
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("SELECT * FROM data WHERE DATE(datetime) = %s", (date,))
    ohlc = cursor.fetchall()
    
    cursor.execute("SELECT * FROM indicators WHERE DATE(datetime) = %s", (date,))
    indicators = cursor.fetchall()
    
    conn.close()
    return jsonify({"ohlc": ohlc, "indicators": indicators})

if __name__ == '__main__':
    create_tables()
    fetch_and_store_nifty_data()
    calculate_and_store_bollinger_bands()
    app.run(debug=True)
