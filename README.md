# 🎓 Online Classes Auto-Joiner (Bot)

An automated Python script designed to monitor your Google Classroom streams and automatically join scheduled classes on **Google Meet** and **Microsoft Teams**. It handles everything from checking your timetable to muting your mic and camera.

---

## 🚀 Features

- **Multi-Platform Support**: Automatically joins **Google Meet** and **Microsoft Teams**.
- **Timetable-Based Automation**: Only runs when you have a scheduled class.
- **Smart Monitoring**: Refreshing the Google Classroom wall every minute to catch new links.
- **Privacy First**: Automatically turns off **Microphone** and **Camera** before joining.
- **Teams Guest Support**: Automatically enters your name if joining MS Teams as a guest.
- **Hands-Free**: Bypasses browser popups (like "Open Microsoft Teams") using hardware-level keyboard simulation.

---

## 🛠️ Prerequisites

Before you start, ensure you have the following installed:

1.  **Python 3.8+**: [Download here](https://www.python.org/downloads/) (Ensure "Add Python to PATH" is checked).
2.  **Google Chrome**: The standard browser.
3.  **ChromeDriver**: Managed automatically by Selenium 4 (service should be up to date).

---

## 📥 Installation

1.  **Extract the files** (or clone this repository) to your local machine.
2.  **Open a Terminal/PowerShell** in the project folder and install the required libraries:

    ```bash
    pip install -r requirements.txt
    ```

    *If `requirements.txt` fails, manually run:*
    ```bash
    pip install selenium python-dotenv pyautogui
    ```

---

## ⚙️ Configuration

The bot uses a `.env` file for your private data.

1.  Create a file named `.env` in the root directory (you can copy `.env.template.no_transcription.for no transcription`).
2.  Fill in the following details:

### 1. Chrome Profile Path
The bot needs to use your logged-in Chrome profile.
- **Windows**: `C:\Users\<Your_User>\AppData\Local\Google\Chrome\User Data`
- **Profile Directory**: Usually `Default` or `Profile 1`.
  *Note: To find your profile path, type `chrome://version` in Chrome.*

### 2. Google Classroom Links
Add the URL for each subject's "Stream" page.
```env
GCR_DF="https://classroom.google.com/u/0/c/YOUR_ID_HERE"
GCR_AI="https://classroom.google.com/u/0/c/YOUR_ID_HERE"
```

### 3. Timetable (JSON Format)
This tells the bot when to look for links. **Important:** The `env_link` key must match the variable name you defined for the GCR link above.

```json
TIMETABLE='{
  "Monday": [
    {"subject": "DF", "start": "08:30", "end": "09:50", "env_link": "GCR_DF"}
  ],
  "Tuesday": [
    {"subject": "AI", "start": "11:30", "end": "12:50", "env_link": "GCR_AI"}
  ]
}'
```

---

## 🏃 Running the Bot

1.  **CRITICAL**: Close all existing Chrome windows using the profile specified in `.env`. Chrome does not allow two instances to use the same profile simultaneously.
2.  **Start the script**:

    ```bash
    python "Autobot without transcription.py"
    ```

3.  The bot will monitor the schedule. When a class is starting, it will launch the browser, find the join link, mute your mic/cam, and join automatically.

---

## ⚠️ Important Notes

- **Popup Blocking**: The script uses **PyAutoGUI** to dismiss the "Open Microsoft Teams" system popups. **Avoid moving your mouse or typing while the bot is joining a Teams meeting.**
- **Headless Mode**: This bot does **not** run in "headless" mode. It will open a physical browser window so you can watch what it's doing (and because many sites block headless automation).
- **Guest Name**: If joining Teams as a guest, it will automatically enter the name specified in the code (currently set to "Aatif Ali").

---

## 📂 Project Structure

- `Autobot without transcription.py`: The core automation logic.
- `.env`: Your private configuration (Links & Timetable).
- `requirements.txt`: Python package dependencies.
