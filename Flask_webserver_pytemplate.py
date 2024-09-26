# Importing necessary libraries and modules
from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import os
import subprocess
import yfinance as yf
from fuzzywuzzy import process
import sys
import json
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import requests
from twilio.rest import Client
import threading
import time

# Create a Flask application instance
app = Flask(__name__)

# Twilio account SID and authentication token
account_sid = '654651645165545'
auth_token = "4465498644464467"

# Create a Twilio client object for sending SMS
client = Client(account_sid, auth_token)

# URL for the news API
apiurl = "xoxoxoxooxoxoxo.api.keys.com.check.the.website"

# Function to send an SMS with the article title
def send_sms(article_title):
    message = client.messages.create(
        body=article_title,
        from_='+4465456545',  # Your Twilio phone number
        to='54546546544'  # The recipient's phone number
    )
    print(f"Message sent with SID: {message.sid}")

# Function to check for new news and send SMS if new articles are found
def check_news():
    last_total_results = 0

    while True:
        response = requests.get(apiurl).text  # Send a request to the news API
        response_json = json.loads(response)  # Load the JSON response
        total_results = response_json.get('totalResults', 0)  # Get total results from the API
        
        if total_results > last_total_results:  # Check if there are new articles
            articles = response_json['articles']
            for article in articles:
                send_sms(article['title'])  # Send SMS for each new article
            last_total_results = total_results  # Update the count of total results
        
        time.sleep(60)  # Wait for 1 minute before checking again

# Start a background thread to run the check_news function
def start_background_task():
    thread = threading.Thread(target=check_news)  # Create a new thread for the check_news function
    thread.daemon = True  # Daemonize the thread
    thread.start()  # Start the thread

@app.route("/")
def index():
    return "News monitoring and SMS service is running."  # Simple message for the root route

# Load stock tickers from a JSON file
def load_tickers_from_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        tickers = json.load(file)  # Load the JSON content
    return tickers

# Load Nifty 50 stock tickers from a JSON file
nifty50_tickers = load_tickers_from_json(r'C:\Users\Desktop\flask_website\stocks_ticker.json')

# Function to search for the best matching ticker
def search_ticker(stock_name):
    best_match, _ = process.extractOne(stock_name.upper(), nifty50_tickers.keys())  # Use fuzzy matching
    return nifty50_tickers[best_match]  # Return the best match

# Function to get the current market price of a stock
def get_current_market_price(stock_name_or_ticker):
    ticker = nifty50_tickers.get(stock_name_or_ticker.upper(), search_ticker(stock_name_or_ticker))  # Get the ticker symbol
    stock = yf.Ticker(ticker)  # Create a Ticker object for the stock

    # Get real-time market data
    current_price = stock.history(period="1d")['Close'][0]  # Get the closing price for today
    current_price = round(current_price, 2)  # Round to 2 decimal places

    previous_close = stock.info['previousClose']  # Get the previous close price

    todays_gains = round(current_price - previous_close, 2)  # Calculate today's gains

    volume = stock.info['volume']  # Get the trading volume

    # Get the most recent analyst rating
    analyst_ratings = stock.recommendations.tail(1)  
    if not analyst_ratings.empty and 'To Grade' in analyst_ratings.columns:
        rating_summary = analyst_ratings['To Grade'].values[0]  # Get the rating
    else:
        rating_summary = "N/A"  # Default if no rating available

    # Get price targets
    target_high_price = stock.info.get('targetHighPrice', 'N/A')
    target_low_price = stock.info.get('targetLowPrice', 'N/A')
    target_mean_price = stock.info.get('targetMeanPrice', 'N/A')
    price_targets = {
        "High": target_high_price,
        "Low": target_low_price,
        "Mean": target_mean_price
    }

    stock_name = stock.info.get('shortName', 'N/A')  # Get the stock name

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

    return stock_data  # Return the stock data

# Function to scrape news from a website
def scrape_news():
    options = Options()  # Set up the WebDriver options
    options.add_argument("--headless")  # Run in headless mode

    driver = webdriver.Firefox(options=options)  # Create a WebDriver instance
    driver.get("https://economictimes.indiatimes.com/markets/stocks/news")  # Navigate to the news page

    # Wait for the page to load and news items to be present
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "eachStory"))  # Wait until news items are loaded
        )
    except Exception as e:
        print(f"error")
        driver.quit()  # Close the WebDriver
        return []

    # Use Selenium to get the page source after all dynamic content is loaded
    html = driver.page_source
    driver.quit()  # Close the WebDriver

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Find all news items by class name
    news_items = soup.find_all('div', class_='eachStory')

    news_data = []  # Initialize a list to hold news data

    for item in news_items:
        try:
            # Extract the title and URL
            title_element = item.find('h3').find('a')
            title = title_element.text.strip()  # Get the title text
            url = title_element['href']  # Get the article URL

            # Extract the time
            time_element = item.find('time')
            publish_time = time_element.text.strip()  # Get the publish time

            # Extract the paragraph description
            description_element = item.find('p')
            description = description_element.text.strip()  # Get the description text

            # Append data to the list
            news_data.append({
                "title": title,
                "url": url,
                "time": publish_time,
                "description": description
            })

        except Exception as e:
            print(f"An error occurred while processing an item: {str(e)}")  # Handle any exceptions

    return news_data  # Return the scraped news data

# Function to get the index values for the navigation bar
def get_index_values():
    indices = {
        'Nifty 50': yf.Ticker('^NSEI').history(period='1d')['Close'][0],  # Get Nifty 50 value
        'India VIX': yf.Ticker('^INDIAVIX').history(period='1d')['Close'][0],  # Get India VIX value
        'Bank Nifty': yf.Ticker('^NSEBANK').history(period='1d')['Close'][0]  # Get Bank Nifty value
    }
    return indices  # Return the indices values

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stock.db"  # Set the URI for the main database
app.config["SQLALCHEMY_BINDS"] = {
    'news_db': 'sqlite:///new.db'  # Set the URI for the news database
}

db = SQLAlchemy(app)  # Create a SQLAlchemy object for database operations

# Define the Todo model for storing stock data
class Todo(db.Model):
    sno = db.Column(db.Integer, primary_key=True)  # Serial number (primary key)
    stock = db.Column(db.String(500), nullable=False)  # Stock name
    cmp = db.Column(db.Integer, nullable=False)  # Current market price
    news = db.Column(db.Integer, nullable=True)  # News ID (nullable)
    previous_close = db.Column(db.Float, nullable=False)  # Previous close price
    todays_gains = db.Column(db.Float, nullable=False)  # Today's gains
    volume = db.Column(db.Integer, nullable=False)  # Trading volume
    analyst_ratings = db.Column(db.String(500), nullable=False)  # Analyst ratings
    price_targets = db.Column(db.String(500),
