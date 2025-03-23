import os
import time
import requests
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s]: %(message)s',
    '%Y-%m-%d %H:%M:%S'
))

# File handler
file_handler = logging.FileHandler('logfile.log')
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s]: %(message)s',
    '%Y-%m-%d %H:%M:%S'
))

# Adding handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Load environment variables
load_dotenv()

# Constants from environment
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
LOGIN_URL = os.getenv("LOGIN_URL")
RESERVATION_URL = os.getenv("RESERVATION_URL")
NTFY_SERVER = os.getenv("NTFY_SERVER")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

def login(driver):
    logger.info("Logging in...")
    driver.get(LOGIN_URL)
    time.sleep(2)

    username_input = driver.find_element(By.NAME, 'username')
    password_input = driver.find_element(By.NAME, 'password')

    username_input.send_keys(USERNAME)
    password_input.send_keys(PASSWORD)
    password_input.send_keys(Keys.RETURN)
    time.sleep(2)
    logger.info("Logged in successfully.")

def send_ntfy_notification(message):
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    response = requests.post(url, data=message.encode('utf-8'))
    if response.ok:
        logger.info("Notification sent successfully.")
    else:
        logger.error(f"Failed to send notification: {response.status_code}")

def check_next_week(driver):
    driver.get(RESERVATION_URL)
    time.sleep(2)

    current_week = driver.find_element(By.ID, 'date_interval').text
    logger.info(f"Current week: {current_week}")

    driver.execute_script("load_reservations(week_number + 1);")
    time.sleep(2)

    next_week = driver.find_element(By.ID, 'date_interval').text

    if "Nincs dátum" in next_week:
        logger.info("Next week is not yet available.")
        return False
    else:
        notification = f"Next week's reservations are now available: {next_week}"
        logger.info(notification)
        send_ntfy_notification(notification)
        return True

def main():
    send_ntfy_notification("Test notification")

    options = Options()
    options.binary_location = '/usr/bin/chromium'
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)
    login(driver)

    try:
        notified = False
        while not notified:
            notified = check_next_week(driver)
            if not notified:
                logger.info("Waiting 300 seconds before next check...")
                time.sleep(300)
            else:
                logger.info("Reservation availability confirmed. Exiting.")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        driver.quit()
        logger.info("Driver closed.")

if __name__ == "__main__":
    main()
