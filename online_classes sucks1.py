import os
import time
import json
from datetime import datetime
import re
import urllib.parse
import pyautogui

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

load_dotenv()

CHROME_PROFILE_PATH = os.getenv("CHROME_PROFILE_PATH", r"Your class chrome profile path")
PROFILE_DIRECTORY = os.getenv("PROFILE_DIRECTORY", "Default")

CHECK_INTERVAL_SECONDS = 60 

try:
    TIMETABLE = json.loads(os.getenv("TIMETABLE", "{}"))
except json.JSONDecodeError:
    print("Error parsing TIMETABLE from .env. Make sure it is valid JSON.")
    TIMETABLE = {}

def get_current_class_info():
    """Checks the timetable to see if a class is currently active."""
    now = datetime.now()
    current_day = now.strftime('%A')
    
    todays_classes = TIMETABLE.get(current_day, [])
    current_time_obj = now.time()
    
    for cls in todays_classes:
        start_time_obj = datetime.strptime(cls['start'], '%H:%M').time()
        end_time_obj = datetime.strptime(cls['end'], '%H:%M').time()
        
        if start_time_obj <= current_time_obj <= end_time_obj:
            env_link_key = cls['env_link']
            gcr_link = os.getenv(env_link_key)
            if not gcr_link or gcr_link.startswith("REPLACE_"):
                print(f"[!] Warning: GCR link for {cls['subject']} not found or not set in .env")
                return None
            return {
                "subject": cls["subject"],
                "gcr_link": gcr_link,
                "end_time": end_time_obj
            }
    return None

def setup_driver():
    """Configures and launches the Chrome browser using your profile"""
    chrome_options = Options()
    
    chrome_options.add_argument(f"user-data-dir={CHROME_PROFILE_PATH}")
    chrome_options.add_argument(f"profile-directory={PROFILE_DIRECTORY}")
    
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    chrome_options.add_argument("--start-maximized")
    
    prefs = {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.notifications": 2,
        
        "protocol_handler.excluded_schemes": {"msteams": False},
        "custom_handlers.enabled": False
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    print("Launching Chrome...")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def check_if_recent(text, link_url, subject=""):
    try:
        index = text.find(link_url)
        if index == -1:
            match = re.search(r"(?:meet\.google\.com|zoom\.us/j|teams\.microsoft\.com)[^\s\"'>]+", link_url)
            if match:
                index = text.find(match.group(0))
                
        if index == -1:
            return True
            
        if subject == "DF":
            snippet_wide = text[max(0, index-800):index+800].lower()
            if "recurring meeting link" in snippet_wide or "every monday class of df6a" in snippet_wide:
                print("[*] Detected recurring DF class link! Bypassing 20-minute age limit.")
                return True

        snippet = text[:index][-600:] 
        
        lower_snip = snippet.lower()
        if "yesterday" in lower_snip:
            return False
            
        months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        for month in months:
            if re.search(rf"\b{month}\s+\d{{1,2}}\b", lower_snip) or re.search(rf"\b\d{{1,2}}\s+{month}\b", lower_snip):
                return False

        time_matches = re.findall(r"(\d{1,2}:\d{2}(?:\s*(?:AM|PM|am|pm))?)", snippet)
        if not time_matches:
            return True
            
        post_time_str = time_matches[-1].strip().upper()
        if "AM" in post_time_str or "PM" in post_time_str:
            parsed_time = datetime.strptime(post_time_str, "%I:%M %p").time()
        else:
            parsed_time = datetime.strptime(post_time_str, "%H:%M").time()
        
        now = datetime.now()
        post_dt = datetime.combine(now.date(), parsed_time)
        
        diff_mins = (now - post_dt).total_seconds() / 60.0
        
        if -10 <= diff_mins <= 20: 
            return True
        else:
            print(f"[-] Link is too old or from a past class. Ignoring.")
            return False

    except Exception as e:
        return True

def find_meeting_links(driver, text):
    meet_pattern = r"(?:https://)?meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}"
    zoom_pattern = r"(?:https://)?[\w-]*\.zoom\.us/j/\d+(?:\?pwd=[\w]+)?"
    teams_pattern = r"(?:https://)?teams\.(?:microsoft|live)\.com/(?:l/meetup-join/|meet/)[^\s]+"
    
    seen = set()
    ordered_links = []
    
    def add_link(link_url):
        if link_url:
            if not link_url.startswith("http"):
                link_url = "https://" + link_url
            if link_url not in seen:
                seen.add(link_url)
                ordered_links.append(link_url)
            
    try:
        a_tags = driver.find_elements(By.TAG_NAME, "a")
        for a in a_tags:
            href = a.get_attribute("href")
            if href:
                decoded_href = urllib.parse.unquote(href)
                if "meet.google.com/" in decoded_href or "zoom.us/j/" in decoded_href or "teams.microsoft.com" in decoded_href or "teams.live.com" in decoded_href:
                    add_link(href)
    except Exception as e:
        print(f"Error checking a-tags for links: {e}")

    for match in re.findall(meet_pattern, text): add_link(match)
    for match in re.findall(zoom_pattern, text): add_link(match)
    for match in re.findall(teams_pattern, text): add_link(match)
    
    return ordered_links

def join_google_meet(driver, url):
    """Navigates to the Google Meet link, mutes mic/video, and joins"""
    print(f"\n[+] Joining Google Meet: {url}")
    driver.get(url)
    
    try:
        wait = WebDriverWait(driver, 15)
        print("Waiting for pre-join screen...")
        time.sleep(5) 
        
        actions = ActionChains(driver)
        print("Turning off Microphone (Ctrl+D)...")
        actions.key_down(Keys.CONTROL).send_keys('d').key_up(Keys.CONTROL).perform()
        time.sleep(2)
        
        print("Turning off Camera (Ctrl+E)...")
        actions.key_down(Keys.CONTROL).send_keys('e').key_up(Keys.CONTROL).perform()
        time.sleep(2)
        
        print("Finding Join button...")
        join_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Join now') or contains(text(), 'Ask to join')]")))
        join_button.click()
        
        print("Successfully clicked the Join button!")
        return True
        
    except Exception as e:
        print(f"[-] Could not join Google Meet automatically. Error: {e}")
        return False

def join_teams_meeting(driver, url):
    """Navigates to the Teams link, attempts to use the web version"""
    print(f"\n[+] Joining Microsoft Teams: {url}")
    driver.get(url)
    
    try:
        wait = WebDriverWait(driver, 20)
        actions = ActionChains(driver)

        # 1. Wait out any potential popup delays
        print("Waiting for 'Open Microsoft Teams' OS popup to appear...")
        time.sleep(4)
        
        print("Simulating hardware ESCAPE key multiple times to ensure popup is dismissed...")
        for _ in range(4):
            pyautogui.press('esc')
            time.sleep(1)
            
        try:
            print("Looking for 'Continue on this browser' button...")
            time.sleep(3)
            
            browser_btn = None
            try:
                browser_btn = driver.find_element(By.ID, "joinOnWeb")
            except:
                pass

            if not browser_btn:
                try:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        if "Continue on this browser" in btn.text:
                            browser_btn = btn
                            break
                except:
                    pass
            
            if browser_btn:
                print("Found the button! Attempting to click via pure Javascript...")
                # We strictly use Javascript to click because native popups invisibly swallow standard clicks!
                driver.execute_script("arguments[0].click();", browser_btn)
                print("Selected 'Continue on this browser'.")
            else:
                print("Critical: Could not find the 'Continue on this browser' button anywhere in the DOM.")
                
        except Exception as e:
            print(f"Error during 'Continue on this browser' interaction: {e}")
            
        print("Waiting for Teams pre-join screen (this can take up to 25 seconds for the web app)...")
        time.sleep(25) 
        
        try:
            print("Checking if Guest Name input is required...")
            inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                placeholder = inp.get_attribute("placeholder")
                if placeholder and "Type your name" in placeholder:
                    print("Guest mode detected. Entering name 'Aatif Ali'...")
                    inp.click()
                    inp.clear()
                    inp.send_keys("Aatif Ali")
                    time.sleep(1)
                    break 
        except Exception as e:
            pass

        try:
            driver.find_element(By.TAG_NAME, "body").click()
        except:
            pass
            
        print("Turning off Microphone (Ctrl+Shift+M)...")
        actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys('m').key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
        time.sleep(3)
        
        print("Turning off Camera (Ctrl+Shift+O)...")
        actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys('o').key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
        time.sleep(3)
        
        try:
            print("Finding Join button...")
            join_btn = None
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "Join" in btn.text or "Join now" in btn.text:
                        join_btn = btn
                        break
            except:
                pass
                
            if join_btn:
                try:
                    join_btn.click()
                except:
                    driver.execute_script("arguments[0].click();", join_btn)
                print("Successfully clicked the Teams Join button!")
            else:
                print("Could not locate the 'Join now' button anywhere in the DOM.")
        except Exception as e:
            print(f"Error finding Join button: {e}")
            
        print("Teams page loaded. The script will keep the browser open.")
        return True
        
    except Exception as e:
        print(f"[-] Could not interact with Teams automatically. Error: {e}")
        return False

def main():
    global STOP_LISTENING
    print("==================================================")
    print("   Google Classroom Auto-Joiner Started")
    print("==================================================")
    
    print("Make sure your normal Chrome windows are CLOSED.")
    
    try:
        while True:
            current_class = get_current_class_info()
            now = datetime.now()
            
            if not current_class:
                print(f"\n[{now.strftime('%H:%M:%S')}] No class currently active. Sleeping for 1 minute...")
                time.sleep(60)
                continue
                
            print(f"\n[{now.strftime('%H:%M:%S')}] Active class found: {current_class['subject']}. Class ends at {current_class['end_time'].strftime('%H:%M')}.")
            
            try:
                driver = setup_driver()
            except Exception as e:
                print(f"\n[!] Failed to start Chrome. Make sure Chrome is totally closed and profile path is correct.\nError: {e}")
                time.sleep(60)
                continue

            processed_links = set()
            first_run = True
            class_ended_flag = False
            
            try:
                while True:
                    if datetime.now().time() > current_class["end_time"]:
                        print(f"\n[!] Class {current_class['subject']} has ended. Closing Chrome.")
                        class_ended_flag = True
                        break
                        
                    current_time = time.strftime('%H:%M:%S')
                    print(f"\n[{current_time}] Refreshing Google Classroom stream for {current_class['subject']}...")
                    
                    driver.get(current_class["gcr_link"])
                    time.sleep(10)
                    driver.execute_script("window.scrollTo(0, 500);")
                    time.sleep(2)
                    
                    page_text = driver.find_element(By.TAG_NAME, "body").text
                    links = find_meeting_links(driver, page_text)
                    
                    links_to_test = []
                    found_new = False
                    
                    if first_run:
                        print(f"[*] Initial scan complete. Found {len(links)} existing links on the wall.")
                        for link in links:
                            processed_links.add(link)
                            
                        if links:
                            first_link = links[0]
                            print(f"\n[*] Validating the most recent link: {first_link}")
                            if check_if_recent(page_text, first_link, current_class["subject"]):
                                print("[+] Link passed validation constraints. Testing it!")
                                links_to_test.append(first_link)
                            else:
                                print("[-] Most recent link is an old class. Ignoring.")
                            
                        print("[*] Now actively monitoring for NEW posts...")
                        first_run = False
                    else:
                        for link in links:
                            if link not in processed_links:
                                print(f"[*] New meeting link detected: {link}")
                                processed_links.add(link)
                                if check_if_recent(page_text, link, current_class["subject"]):
                                    links_to_test.append(link)
                                    found_new = True
                                else:
                                    print(f"[-] Ignored {link} as it violates the 20-minute/same-day constraint.")
                    
                    for link in links_to_test:
                        decoded_link = urllib.parse.unquote(link)
                        join_success = False
                        
                        if "meet.google.com" in decoded_link:
                            join_success = join_google_meet(driver, link)
                        elif "zoom.us" in decoded_link:
                            print(f"[!] Zoom Link found: {link}. Auto-join inside browser not fully implemented yet.")
                            join_success = False
                        elif "teams.microsoft.com" in decoded_link or "teams.live.com" in decoded_link:
                            join_success = join_teams_meeting(driver, link)
                            
                        if join_success:
                            print("Meeting joined successfully. Resting until class ends...")
                            
                            while datetime.now().time() <= current_class["end_time"]:
                                time.sleep(10)
                                
                            class_ended_flag = True
                            print(f"\n[!] Class {current_class['subject']} has ended. Closing Chrome.")
                            break
                        else:
                            print("[-] Meeting join failed or unsupported. Returning to monitor stream...")
                                
                    if class_ended_flag:
                        break
                        
                    if not first_run and not links_to_test:
                        print(f"No new links found. Waiting {CHECK_INTERVAL_SECONDS} seconds until next check...")
                        
                    time.sleep(CHECK_INTERVAL_SECONDS)
                    
            finally:
                print("Closing Chrome browser tab to return to monitoring...")
                try:
                    driver.quit()
                except:
                    pass
            
            print("Waiting for next class...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n[+] Script stopped by user (Ctrl+C).")

if __name__ == "__main__":
    main()
