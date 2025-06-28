import os
import time
import json
import logging
import subprocess
import requests
import random
from datetime import date
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

log_format = logging.Formatter(
    "%(asctime)s [%(levelname)s]: %(message)s", "%Y-%m-%d %H:%M:%S"
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)

file_handler = logging.FileHandler("logfile.log")
file_handler.setFormatter(log_format)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

# --- Environment Setup ---
load_dotenv()

BW_ITEM_ID = "63b2b6ac-dcfe-409c-879d-b13800e2258e"
LOGIN_URL = "https://mmmk.sch.bme.hu/login"
RESERVATION_URL = "https://mmmk.sch.bme.hu/foglalas"
NTFY_SERVER = os.getenv("NTFY_SERVER")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "mmmk_notifications")


def bw_get_credentials():
    logger.info("Fetching credentials from Bitwarden...")
    subprocess.run(["bw", "login"])
    print("Please type BW master password:")

    result = subprocess.run(
        ["bw", "get", "item", BW_ITEM_ID], capture_output=True, text=True
    )

    if result.returncode != 0:
        logger.error("Failed to retrieve credentials. Check Bitwarden password.")
        exit(1)

    try:
        item = json.loads(result.stdout)
        username = item["login"]["username"]
        password = item["login"]["password"]
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to parse Bitwarden response: {e}")
        exit(1)

    logger.info("Credentials retrieved successfully.")
    return username, password


def send_ntfy_notification(message):
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}"
    try:
        response = requests.post(url, data=message.encode("utf-8"))
        if response.ok:
            logger.info("Notification sent.")
        else:
            logger.warning(f"Notification failed: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"Error sending notification: {e}")


def login(driver, username, password):
    logger.info("Logging in...")
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 10)

    try:
        username_input = wait.until(
            EC.visibility_of_element_located((By.NAME, "username"))
        )
        password_input = driver.find_element(By.NAME, "password")

        username_input.send_keys(username)
        password_input.send_keys(password)
        password_input.send_keys(Keys.RETURN)

        wait.until(EC.invisibility_of_element_located((By.NAME, "username")))
        logger.info("Login successful.")
    except TimeoutException:
        logger.error("Login failed. Username field did not disappear.")
        exit(1)


def check_next_week(driver, current_date):
    logger.info("Checking next week's reservations...")
    driver.get(RESERVATION_URL)

    wait = WebDriverWait(driver, 10)
    current_week_text = wait.until(
        EC.visibility_of_element_located((By.ID, "date_interval"))
    ).text

    try:
        year, month, day_range = current_week_text.split(".")
        start_day, _ = map(int, day_range.split("-"))
        start_date = date(int(year), int(month), start_day)
    except Exception as e:
        logger.error(f"Error parsing date interval: {current_week_text} — {e}")
        return None

    if current_date < start_date:
        return current_week_text

    logger.info(f"Current week: {current_week_text}")
    driver.execute_script("load_reservations(week_number + 1);")

    time.sleep(2)  # Allow script to execute
    next_week_text = wait.until(
        EC.visibility_of_element_located((By.ID, "date_interval"))
    ).text

    if "Nincs dátum" in next_week_text:
        logger.info("Next week is not available yet.")
        return None

    return next_week_text


def load_reservation_list(filename="reservation_list.json"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            reservations = json.load(f)

        if not isinstance(reservations, list):
            raise ValueError("Reservation list must be a list of strings.")

        logger.info(f"Loaded {len(reservations)} reservation(s) from {filename}.")
        return reservations

    except FileNotFoundError:
        logger.error(f"Reservation file '{filename}' not found.")
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in '{filename}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading reservation file: {e}")

    return []


def make_reservations(driver, reservation_list):
    logger.info("Making reservations...")

    wait = WebDriverWait(driver, 10)

    for reservation in reservation_list:
        try:
            day, time_str = reservation.split()
            selector = f'div[data-day="{day.lower()}"][data-hour="{time_str}"]'

            cell = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )

            if "Szabad" in str(cell.get_attribute("innerHTML")):
                cell.click()
                logger.info(f"Reserved: {day} {time_str}")
            else:
                logger.info(f"Slot not available: {day} {time_str}")
        except TimeoutException:
            logger.warning(f"Reservation slot not found: {reservation}")
        except Exception as e:
            logger.error(f"Error processing reservation '{reservation}': {e}")

    try:
        save_button = wait.until(EC.element_to_be_clickable((By.ID, "save")))
        save_button.click()
        logger.info("Clicked 'Mentés' to save reservations.")
        time.sleep(5)
    except TimeoutException:
        logger.error("Could not find or click the 'Mentés' button.")


def get_driver():
    logger.info("Setting up Firefox WebDriver in headless mode...")

    options = FirefoxOptions()
    options.add_argument("--headless")

    try:
        driver_path = GeckoDriverManager().install()
        logger.info(f"GeckoDriver installed at: {driver_path}")

        driver = webdriver.Firefox(service=FirefoxService(driver_path), options=options)
        logger.info("Firefox WebDriver initialized successfully.")
        return driver
    except Exception as e:
        logger.exception("Failed to initialize Firefox WebDriver.")
        raise


def main():

    current_date = date.today()

    send_ntfy_notification("Test notification")
    driver = get_driver()
    reservation_list = load_reservation_list("reservation_list.json")

    username, password = bw_get_credentials()

    try:
        login(driver, username, password)

        while True:
            next_week = check_next_week(driver, current_date)
            if next_week:
                message = f"Next week's reservations are now available: {next_week}"
                logger.info(message)
                send_ntfy_notification(message)
                make_reservations(driver, reservation_list)
                break

            # Wait and try again
            sleep_time = random.randint(55, 75)
            logger.info(f"Waiting {sleep_time} seconds before next check...")
            time.sleep(sleep_time)

    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Exiting.")
    finally:
        driver.quit()
        logger.info("Driver closed.")


if __name__ == "__main__":
    main()
