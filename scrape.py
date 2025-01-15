###
# Setup:
# 0. Make sure you have a Python 3.9+ environment and a GCP project with Google Sheets API enabled
# 1. pip install python-dotenv gspread bs4 google-api-python-client google-auth-httplib2 google-auth-oauthlib
# 2. Rename .env.example file to .env and update with your Google Sheet ID, Sheet Name, and Column Numbers
# 3. Download your GCP service account credentials JSON file and save it as credentials.json
#
# Note: The script will update the Google Sheet with the latest GoFundMe raised amount every 5 minutes.
#       In the event of a timeout or error (such as hitting the rate limit), try re-running the script.
# Questions? Contact Author: benmbenjamin@gmail.com
###

import os
import requests
import time
import gspread
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)

# Get column numbers from .env file
gfm_url_col = int(os.environ.get("SHEET_GFM_URL_COL"))
gfm_raised_col = int(os.environ.get("SHEET_GFM_RAISED_COL"))
gfm_goal_col = int(os.environ.get("SHEET_GFM_GOAL_COL"))

# Convert 1-based column numbers to 0-based indices for user-friendly config
gfm_url_col_idx = gfm_url_col - 1
gfm_raised_col_idx = gfm_raised_col - 1
gfm_goal_col_idx = gfm_goal_col - 1

def fetch_html(url):
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.text

def extract_value(html):
    soup = BeautifulSoup(html, 'html.parser')
    span = soup.find('span', class_='progress-meter_progressBarHeading__Nxc77')
    if span:
        inner_span = span.find('span')
        if inner_span:
            return inner_span.text
    return None

def extract_goal(html):
    start_str = '"goalAmount":{"__typename":"Money","amount":'
    start_idx = html.find(start_str)
    if start_idx != -1:
        start_idx += len(start_str)
        end_idx = html.find(',', start_idx)
        if end_idx != -1:
            goal_amount = html[start_idx:end_idx]
            return f"${int(goal_amount):,}"
    return None

def get_links_from_sheet(sheet_url, sheet_name):
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    data = sheet.get_all_values()
    gfmrows = list(filter(lambda row: row[6].startswith('https://www.gofundme.com'), data))
    links = list(map(lambda row: row[6], gfmrows))
    return links

def update_sheet(sheet_url, sheet_name, start=None, end=None):
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).worksheet(sheet_name)
    data = sheet.get_all_values()
    s = start - 1 if start else 0
    e = end or len(data)
    for idx, row in enumerate(data[s:e], start=s):
        try:
          if row[gfm_url_col_idx].startswith('https://www.gofundme.com') or row[6].startswith('https://gofund.me'):
              html = fetch_html(row[gfm_url_col_idx])
              value = extract_value(html)
              goal = extract_goal(html)
              if value and value != row[gfm_raised_col_idx] and f'{value}.00' != row[gfm_raised_col_idx]:
                print(f'({idx+1}) $$ update for {row[0]}: {value}')
                sheet.update_cell(idx+1, gfm_raised_col, value)
                time.sleep(0.6) # Pause to avoid rate limiting
              if goal and goal != row[gfm_goal_col_idx] and f'{goal}.00' != row[gfm_goal_col_idx]:
                print(f'****({idx+1}) Goal for {row[0]}: {goal}')
                sheet.update_cell(idx+1, gfm_goal_col, goal)
                time.sleep(0.6) # Pause to avoid rate limiting
        except Exception as e:
            print(f'****************ERROR**************** ({idx+1}): {e}')
            continue

def countdown(t):
    while t:
        mins, secs = divmod(t, 60)
        timer = 'Next run in {:02d}:{:02d}'.format(mins, secs)
        print(timer, end="\r")
        time.sleep(1)
        t -= 1

if __name__ == "__main__":
    sheet_id = os.environ.get("SHEET_ID")
    sheet_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/edit'
    sheet_name = os.environ.get("SHEET_NAME")
    start_var = os.environ.get("SHEET_START_ROW", "1")
    end_var = os.environ.get("SHEET_END_ROW")
    start_row = int(start_var)
    end_row = int(end_var) if end_var else None

    update_sheet(sheet_url, sheet_name, start=start_row, end=end_row)

    # while True:
    #   update_sheet(sheet_url, sheet_name)
    #   countdown(300) # 5 minutes