from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import os
import subprocess
import yfinance as yf
from fuzzywuzzy import process
import sys,json
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
import json
from twilio.rest import Client
import threading
import time


app = Flask(__name__)

# twilio keys ! check in their website
account_sid = '654651645165545'
auth_token = "4465498644464467"


# Create a Twilio client object
client = Client(account_sid, auth_token)

# apiurl for the news API
apiurl = "xoxoxoxooxoxoxo.api.keys.com.check.the.website"

# Function to send SMS
def send_sms(article_title):
    message = client.messages.create(
        body=article_title,
        from_='+4465456545',  # Your Twilio phone number
        to='54546546544'  # The recipient's phone number
    )
    print(f"Message sent with SID: {message.sid}")

# Function to check for new news and send SMS
def check_news():
    last_total_results = 0

    while True:
        response = requests.get(apiurl).text
        response_json = json.loads(response)
        total_results = response_json.get('totalResults', 0)
        
        if total_results > last_total_results:
            articles = response_json['articles']
            for article in articles:
                send_sms(article['title'])
            last_total_results = total_results
        
        time.sleep(60)  # Wait for 1 minute before checking again

# Background thread to run the check_news function
def start_background_task():
    thread = threading.Thread(target=check_news)
    thread.daemon = True
    thread.start()

@app.route("/")
def index():
    return "News monitoring and SMS service is running."

def load_tickers_from_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        tickers = json.load(file)
    return tickers

# a json with tickers
nifty50_tickers = load_tickers_from_json(r'C:\Users\Desktop\flask_website\stocks_ticker.json')

def search_ticker(stock_name):
    best_match, _ = process.extractOne(stock_name.upper(), nifty50_tickers.keys())
    return nifty50_tickers[best_match]

def get_current_market_price(stock_name_or_ticker):
    # Fetch the ticker symbol
    ticker = nifty50_tickers.get(stock_name_or_ticker.upper(), search_ticker(stock_name_or_ticker))
    stock = yf.Ticker(ticker)

    # Get real-time market data
    current_price = stock.history(period="1d")['Close'][0]
    current_price = round(current_price, 2)

    # Get the previous close price
    previous_close = stock.info['previousClose']

    # Calculate today's gains (Current Price - Previous Close)
    todays_gains = round(current_price - previous_close, 2)

    # Get volume (real-time market data)
    volume = stock.info['volume']

    # Get analyst ratings (buy, hold, sell recommendations)
    analyst_ratings = stock.recommendations.tail(1)  # Get the most recent analyst rating
    if not analyst_ratings.empty and 'To Grade' in analyst_ratings.columns:
        rating_summary = analyst_ratings['To Grade'].values[0]
    else:
        rating_summary = "N/A"

    # Get price targets
    target_high_price = stock.info.get('targetHighPrice', 'N/A')
    target_low_price = stock.info.get('targetLowPrice', 'N/A')
    target_mean_price = stock.info.get('targetMeanPrice', 'N/A')
    price_targets = {
        "High": target_high_price,
        "Low": target_low_price,
        "Mean": target_mean_price
    }

    # Return the stock name
    stock_name = stock.info.get('shortName', 'N/A')

    # Create a dictionary with all the required information
    stock_data = {
        "Stock Name": stock_name,
        "Current Price": current_price,
        "Previous Close": previous_close,
        "Today's Gains": todays_gains,
        "Volume": volume,
        "Analyst Ratings": rating_summary,
        "Price Targets": price_targets
    }

    return stock_data


#news scrapping functin
def scrape_news():
    # Set up the WebDriver
    options = Options()
    options.add_argument("--headless")

    driver = webdriver.Firefox(options=options)
    driver.get("https://economictimes.indiatimes.com/markets/stocks/news")

    # Wait for the page to load and news items to be present
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "eachStory"))
        )
    except Exception as e:
        print(f"error")
        driver.quit()
        return []

    # Use Selenium to get the page source after all dynamic content is loaded
    html = driver.page_source
    driver.quit()

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Find all news items by class name
    news_items = soup.find_all('div', class_='eachStory')

    news_data = []

    for item in news_items:
        try:
            # Extract the title and URL
            title_element = item.find('h3').find('a')
            title = title_element.text.strip()
            url = title_element['href']

            # Extract the time
            time_element = item.find('time')
            publish_time = time_element.text.strip()

            # Extract the paragraph description
            description_element = item.find('p')
            description = description_element.text.strip()

            # Append data to list
            news_data.append({
                "title": title,
                "url": url,
                "time": publish_time,
                "description": description
            })

        except Exception as e:
            print(f"An error occurred while processing an item: {str(e)}")

    return news_data

#this will give the indices value for nav bar
def get_index_values():
    indices = {
        'Nifty 50': yf.Ticker('^NSEI').history(period='1d')['Close'][0],
        'India VIX': yf.Ticker('^INDIAVIX').history(period='1d')['Close'][0],
        'Bank Nifty': yf.Ticker('^NSEBANK').history(period='1d')['Close'][0]
    }
    return indices

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stock.db"
app.config["SQLALCHEMY_BINDS"] = {
    'news_db': 'sqlite:///new.db'}

db = SQLAlchemy(app)



# here i am defining the database
class Todo(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    stock = db.Column(db.String(500), nullable=False)
    cmp = db.Column(db.Integer, nullable=False)
    news = db.Column(db.Integer, nullable=True)
    previous_close = db.Column(db.Float, nullable=False)
    todays_gains = db.Column(db.Float, nullable=False)
    volume = db.Column(db.Integer, nullable=False)
    analyst_ratings = db.Column(db.String(500), nullable=False)
    price_targets = db.Column(db.String(500), nullable=True)
    def __repr__(self) -> str:
        return f"{self.sno} - {self.news}"

#this is the news database
class News(db.Model):
    __bind_key__ = 'news_db'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date = db.Column(db.String(100), nullable=False)
    
    def __repr__(self) -> str:
        return f"{self.title} - {self.date}"
    


# Check if the database exists before creating it
if not os.path.exists('stock.db'):
    with app.app_context():
        db.create_all()

if not os.path.exists('new.db'):
    with app.app_context():
        db.create_all()


# Static websites
@app.route('/', methods=['GET', 'POST'])

#this is where i am entering the data
def home():
    # This is making the form work
    if request.method == 'POST':
        reqstock = request.form['stock']
        data = get_current_market_price(reqstock)
        print(data["Stock Name"])
        todo = Todo(
            stock=data["Stock Name"], 
            cmp=data["Current Price"], 
            news="N/A",  # or another value if you want to store news data here
            previous_close=data["Previous Close"],
            todays_gains=data["Today's Gains"],
            volume=data["Volume"],
            analyst_ratings=data["Analyst Ratings"],
            price_targets=data["Price Targets"]["Mean"])   
        db.session.add(todo)
        db.session.commit()
        return redirect("/")

    alltodo = Todo.query.all()
    indices = get_index_values()
    return render_template('index.html', alltodo=alltodo,indices=indices)






# Route for News operations
@app.route('/news')
def news():
    start_background_task()
    # Run the scraper script
    # Fetch the latest news data from the database
    news_data = scrape_news()
    # all_news = News.query.all() #might be a mistake here
    return render_template('news.html', all_news=news_data)

    
# New route to handle SMS sending
@app.route('/sms')
def sms():
    # file1.py
    with open('chart.py') as f:
        code = f.read()
        exec(code)

    return redirect('/')  # Redirect back to the news page after sending the SMS













#this is for remove function, so no changes
@app.route('/remove/<int:sno>')
def remove(sno):
    todo = Todo.query.filter_by(sno=sno).first()
    if todo:
        db.session.delete(todo)
        db.session.commit()
    return redirect("/")

if __name__ == '__main__':
    app.run(debug=True)
