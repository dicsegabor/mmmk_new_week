# MMMK Reservation Booker

This script automates the reservation process on the BME MMMK system. It detects when next week's reservations become available, then submits booking requests for specified times, and notifies the user via `ntfy`.

## Features

- Logs in using Bitwarden CLI credentials
- Detects when next week's reservations open
- Automatically books reservations listed in `reservation_list.json`
- Sends push notification via an `ntfy` server
- Uses Firefox in headless mode via Selenium
- Can put the laptop to sleep after successful booking using `run_then_sleep.sh`

---

## Setup

### 1. Clone the project and set up Python environment

```bash
git clone <your-repo-url>
cd mmmk-booker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create `.env` file

Create a `.env` file in the project root with:

```
NTFY_SERVER=http://<your-ntfy-server-ip>:<port>
NTFY_TOPIC=mmmk_notifications
```

Replace `<your-ntfy-server-ip>` with the IP or domain of your `ntfy` server.

### 3. Create the reservation list

Create a `reservation_list.json` file in the root directory, for example:

```json
["saturday 19:00", "saturday 20:00", "saturday 21:00"]
```

Each entry should be a string in the format:  
`<weekday> <HH:MM>` — all lowercase, 24-hour format.

---

## Bitwarden Setup

Ensure the [Bitwarden CLI](https://bitwarden.com/help/cli/) (`bw`) is installed.

Before running the script:

```bash
bw login
```

During execution, you’ll be prompted for your master password to retrieve credentials. Set your `BW_ITEM_ID` inside the script.

---

## Running

### Run normally:

```bash
python main.py
```

### Run and put laptop to sleep after:

```bash
./run_then_sleep.sh
```

Ensure the script is executable:

```bash
chmod +x run_then_sleep.sh
```

---

## Requirements

- Python 3.8+
- Firefox browser installed
- `geckodriver` is auto-managed by `webdriver-manager`
- Bitwarden CLI (`bw`) installed
- A working `ntfy` server

---

## Logs

All activity is logged to `logfile.log` in the current directory.

---

## License

MIT License (or your preferred license)
