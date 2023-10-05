import streamlit as st
import ccxt
import time
import threading


def initialize_woo(api_key, api_secret):
    try:
        exchange = ccxt.woo()
        exchange.apiKey = api_key
        exchange.secret = api_secret
        return exchange
    except Exception as e:
        st.write(f"Failed to initialize Woo: {e}")
        return None

def initialize_bybit(api_key, api_secret):
    try:
        exchange = ccxt.bybit()
        exchange.apiKey = api_key
        exchange.secret = api_secret
        return exchange
    except Exception as e:
        st.write(f"Failed to initialize Bybit: {e}")
        return None

def place_order(exchange, symbol, amount, order_type):
    try:
        order_book = exchange.fetch_order_book(symbol)
        best_price = order_book['bids'][0][0] if order_type == "Long" else order_book['asks'][0][0]
        return exchange.create_limit_buy_order(symbol, amount, best_price) if order_type == "Long" else exchange.create_limit_sell_order(symbol, amount, best_price), best_price
    except Exception as e:
        st.write(f"Error while placing order: {e}")
        return None, None


def manage_order(exchange, order, symbol, best_price, take_profit_percent, take_profit_dollar, order_type):
    try:
        order_status = exchange.fetch_order(order['id'], symbol)
        if order_status['status'] == 'closed':
            st.write(f"Entry filled at {best_price}")
            place_take_profit(exchange, symbol, amount, best_price, take_profit_percent, take_profit_dollar, order_type)
            return True
    except Exception as e:
        st.write(f"Error while checking order: {e}")
        return False

def calculate_asset_amount(exchange, symbol, dollar_value, order_type):
    try:
        order_book = exchange.fetch_order_book(symbol)
        best_price = order_book['bids'][0][0] if order_type == "Long" else order_book['asks'][0][0]
        return dollar_value / best_price
    except Exception as e:
        st.write(f"Error while calculating asset amount: {e}")
        return None
def place_take_profit(exchange, symbol, amount, best_price, take_profit_percent, take_profit_dollar, order_type):
    if take_profit_percent or take_profit_dollar:
        take_profit_price = calculate_take_profit_price(best_price, take_profit_percent, take_profit_dollar, order_type)
        tp_order = exchange.create_limit_sell_order(symbol, amount, take_profit_price) if order_type == "Long" else exchange.create_limit_buy_order(symbol, amount, take_profit_price)
        st.write(f"Take-profit order placed at {take_profit_price}")


def calculate_take_profit_price(best_price, take_profit_percent, take_profit_dollar, order_type):
    if take_profit_percent:
        return best_price * (1 + take_profit_percent / 100) if order_type == "Long" else best_price * (1 - take_profit_percent / 100)
    elif take_profit_dollar:
        return best_price + take_profit_dollar if order_type == "Long" else best_price - take_profit_dollar





def cancel_previous_order(exchange, order, symbol):
    try:
        exchange.cancel_order(order['id'], symbol)
        #st.write(f"Cancelled previous order for {symbol}")
    except Exception as e:
        st.write(f"Error while cancelling order: {e}")

def chase_order(exchange, symbol, amount, sleep_time, take_profit_percent, take_profit_dollar, order_type):
    global is_chasing  # Use the global flag
    if exchange is None:
        st.write("Exchange not initialized. Cannot chase order.")
        return

    log_placeholder.write(f"Starting to chase {order_type.lower()} order...")
    previous_order = None  # Store the previous order here

    while is_chasing:  # Check the flag here
        if previous_order:  # Cancel the previous order if exists
            cancel_previous_order(exchange, previous_order, symbol)

        order, best_price = place_order(exchange, symbol, amount, order_type)
        previous_order = order  # Update the previous order

        if order:
            time.sleep(sleep_time)
            if manage_order(exchange, order, symbol, best_price, take_profit_percent, take_profit_dollar, order_type):
                break

    st.write("Stopped chasing orders.")

# Streamlit UI
st.title('Chase-Limit-Order')
log_placeholder = st.empty()

# Sidebar for API Key Input
st.sidebar.title('API Settings')
exchange_choice = st.sidebar.selectbox("Choose the exchange:", ["Woo", "Bybit"])
api_key = st.sidebar.text_input("Enter API Key:", type="password")
api_secret = st.sidebar.text_input("Enter API Secret:", type="password")


# Initialize the correct exchange based on the selection
if exchange_choice == "Woo":
    exchange = initialize_woo(api_key, api_secret)
    pairs_filename = "woox_pairs.txt"
elif exchange_choice == "Bybit":
    exchange = initialize_bybit(api_key, api_secret)
    pairs_filename = "bybit_perps.txt"

 # Load pairs from the selected file
with open(pairs_filename, "r") as file:
    trading_pairs = [pair.strip() for pair in file.readlines()]
symbol = st.selectbox("Choose the trading pair symbol:", trading_pairs)
dollar_value = st.number_input("Enter the dollar value to trade:", min_value=1.0, max_value=10000.0, value=500.0)
order_type = st.selectbox("Choose the order type:", ["Long", "Short"])
sleep_time = st.slider("Time to wait before checking order status (seconds):", 1, 60, 20)

# Take profit settings
take_profit_option = st.selectbox("Choose take-profit type:", ["None", "Percentage", "Dollar Value"])
take_profit_percent = st.number_input("Enter the take-profit percentage:", min_value=0.01, max_value=100.0, value=1.0) if take_profit_option == "Percentage" else None
take_profit_dollar = st.number_input("Enter the take-profit dollar value:", min_value=0.01, max_value=1000.0, value=1.0) if take_profit_option == "Dollar Value" else None

# Initialize the correct exchange based on the selection
if exchange_choice == "Woo":
    exchange = initialize_woo(api_key, api_secret)
elif exchange_choice == "Bybit":
    exchange = initialize_bybit(api_key, api_secret)

if st.button("Start Chasing Order"):
    is_chasing = True  # Set the flag to True
    exchange = initialize_woo(api_key, api_secret)
    if exchange:
        amount = calculate_asset_amount(exchange, symbol, dollar_value, order_type)
        if amount:
            chase_order(exchange, symbol, amount, sleep_time, take_profit_percent, take_profit_dollar, order_type)
    else:
        st.write("Failed to initialize the exchange. Please check your API keys.")

stop_chasing = st.button("Stop Chasing Order")  # UI button to stop chasing
is_chasing = True  # A flag to control the chasing loop

if stop_chasing:  # If the stop button is clicked
    is_chasing = False  # Set the flag to False

# Add Clear Log button
if st.button("Clear Log"):
    log_placeholder.empty()
