import os
import time
import smtplib
from email.mime.text import MIMEText
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

SMTP_SERVER = os.getenv("SMTP_SERVER","")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_TO = os.getenv("EMAIL_TO","")

def login(driver):
    driver.get(LOGIN_URL)
    time.sleep(2)

    username_input = driver.find_element(By.NAME, 'username')
    password_input = driver.find_element(By.NAME, 'password')

    username_input.send_keys(USERNAME)
    password_input.send_keys(PASSWORD)
    password_input.send_keys(Keys.RETURN)
    time.sleep(2)

def send_email(week_info):
    subject = "Reservation Week Available!"
    body = f"Next week's reservations are now available:\n{week_info}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

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
    else:
        print(f"Next week available: {next_week}")
        send_email(next_week)  # Sends email notification

def main():
    options = Options()
    options.binary_location = '/usr/bin/chromium'
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)

    try:
        login(driver)
        check_next_week(driver)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
