import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants from environment
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
LOGIN_URL = os.getenv("LOGIN_URL")
RESERVATION_URL = os.getenv("RESERVATION_URL")
NTFY_SERVER = os.getenv("NTFY_SERVER", "http://localhost:8080")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "mmmk_notifications")

def login(driver):
    driver.get(LOGIN_URL)
    time.sleep(2)

    username_input = driver.find_element(By.NAME, 'username')
    password_input = driver.find_element(By.NAME, 'password')

    username_input.send_keys(USERNAME)
    password_input.send_keys(PASSWORD)
    password_input.send_keys(Keys.RETURN)
    time.sleep(2)

def send_ntfy_notification(message):
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    requests.post(url, data=message.encode('utf-8'))

def check_next_week(driver):
    driver.get(RESERVATION_URL)
    time.sleep(2)

    current_week = driver.find_element(By.ID, 'date_interval').text
    print(f"Current week: {current_week}")

    driver.execute_script("load_reservations(week_number + 1);")
    time.sleep(2)

    next_week = driver.find_element(By.ID, 'date_interval').text

    if "Nincs dátum" in next_week:
        print("Next week is not yet available.")
        return False
    else:
        notification = f"Next week's reservations are now available: {next_week}"
        print(notification)
        send_ntfy_notification(notification)
        return True

def main():
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
                time.sleep(600)
            else:
                print("Notification sent. Exiting.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
