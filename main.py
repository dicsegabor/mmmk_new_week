import os
import time
import requests
import logging
import subprocess
import json
from datetime import date
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from dotenv import load_dotenv

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s", "%Y-%m-%d %H:%M:%S")
)

# File handler
file_handler = logging.FileHandler("logfile.log")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s", "%Y-%m-%d %H:%M:%S")
)

# Adding handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Load environment variables
load_dotenv()

# Constants from environment
BW_ITEM_ID = "63b2b6ac-dcfe-409c-879d-b13800e2258e"
LOGIN_URL = "https://mmmk.sch.bme.hu/login"
RESERVATION_URL = "https://mmmk.sch.bme.hu/foglalas"
NTFY_SERVER = os.getenv("NTFY_SERVER")
NTFY_TOPIC = "mmmk_notifications"


def bw_get_credentials():
    subprocess.run(["bw", "login"])
    print("Enter BW master password:")
    credentials = subprocess.run(
        ["bw", "get", "item", BW_ITEM_ID], capture_output=True, text=True
    )
    if credentials.returncode != 0:
        print("Error authenticating. Wrong password?")
        exit(1)
    item = json.loads(credentials.stdout)
    return item["login"]["username"], item["login"]["password"]


def login(driver, username, password):
    logger.info("Logging in...")
    driver.get(LOGIN_URL)

    wait = WebDriverWait(driver, 10)
    username_input = wait.until(EC.visibility_of_element_located((By.NAME, "username")))
    password_input = driver.find_element(By.NAME, "password")

    username_input.send_keys(username)
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)

    try:
        # Wait until the username input disappears to confirm login success
        wait.until(EC.invisibility_of_element_located((By.NAME, "username")))
    except TimeoutException:
        logger.error("Login failed — username input still visible.")
        exit(1)

    logger.info("Logged in successfully.")


def send_ntfy_notification(message):
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    response = requests.post(url, data=message.encode("utf-8"))
    if response.ok:
        logger.info("Notification sent successfully.")
    else:
        logger.error(f"Failed to send notification: {response.status_code}")


def check_next_week(driver, current_date):
    driver.get(RESERVATION_URL)

    wait = WebDriverWait(driver, 10)
    current_week = wait.until(
        EC.visibility_of_element_located((By.ID, "date_interval"))
    ).text
    year, month, day_range = current_week.split(".")
    start_day, _ = map(int, day_range.split("-"))
    start_date = date(int(year), int(month), start_day)

    if current_date < start_date:
        return True

    logger.info(f"Current week: {current_week}")

    driver.execute_script("load_reservations(week_number + 1);")

    time.sleep(2)
    next_week = wait.until(
        EC.visibility_of_element_located((By.ID, "date_interval"))
    ).text

    if "Nincs dátum" in next_week:
        logger.info("Next week is not yet available.")
        return False
    else:
        notification = f"Next week's reservations are now available: {next_week}"
        logger.info(notification)
        send_ntfy_notification(notification)
        return True


def main():
    username, password = bw_get_credentials()
    current_date = date.today()

    send_ntfy_notification("Test notification")

    options = Options()
    options.binary_location = "/usr/bin/chromium"
    # options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    login(driver, username, password)

    try:
        notified = False
        while not notified:
            notified = check_next_week(driver, current_date)
            if not notified:
                logger.info("Waiting 60 seconds before next check...")
                time.sleep(60)
            else:
                logger.info("Reservation availability confirmed. Exiting.")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")
    finally:
        driver.quit()
        logger.info("Driver closed.")


if __name__ == "__main__":
    main()
