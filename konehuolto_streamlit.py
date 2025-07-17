import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import pandas as pd

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

try:
    credentials_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(st.secrets["SHEET_NIMI"])
    ws = sheet.worksheet("Huollot")
    rows = ws.get_all_records()
    st.success("Yhteys Google Sheetiin onnistui!")
    df = pd.DataFrame(rows)
    st.dataframe(df)
except Exception as e:
    st.error(f"Virhe yhteydessä Google Sheetiin: {e}")
