import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

# --- Kirjautuminen ---
def login():
    st.title("Kirjaudu sisään")
    username = st.text_input("Käyttäjätunnus")
    password = st.text_input("Salasana", type="password")
    if st.button("Kirjaudu"):
        if username == "mattipa" and password == "jdtoro#":
            st.session_state["logged_in"] = True
        else:
            st.error("Väärä käyttäjätunnus tai salasana.")

if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    login()
    st.stop()

# --- Google Sheets API yhdistäminen ---
def get_gsheet_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(st.secrets["Konehuollot Data"]).sheet1
    return sheet

def lue_data_gsheet():
    sheet = get_gsheet_connection()
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def tallenna_data_gsheet(df):
    sheet = get_gsheet_connection()
    sheet.clear()
    if not df.empty:
        sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- Päätab ---
st.set_page_config(page_title="Konehuolto", layout="wide")
st.title("Konehuolto-ohjelma (Google Sheets -versio)")
tab1, tab2 = st.tabs(["➕ Lisää huolto", "📋 Huoltohistoria"])

# --- Alusta / lue data ---
try:
    df = lue_data_gsheet()
except Exception as e:
    st.error("Ei yhteyttä Google Sheetiin! Tarkista oikeudet ja secrets.")
    st.stop()

# --- Lisää huolto ---
with tab1:
    st.header("Lisää uusi huoltotapahtuma")

    # Nämä arvot voit laajentaa tarpeen mukaan!
    kone_nimi = st.text_input("Koneen nimi")
    ryhma = st.text_input("Ryhmä")
    tunnit = st.text_input("Tunnit/km")
    pvm = st.date_input("Päivämäärä", value=datetime.today())
    vapaa = st.text_input("Huom")
    # Lisää tarvittaessa lisää huoltokohteita
    huoltokohteet = ["MÖ", "HÖ", "AÖ", "IS", "MS", "HS", "R", "PS", "T", "VÖ", "PÖ"]
    huollot = {}
    cols = st.columns(6)
    for i, kohta in enumerate(huoltokohteet):
        with cols[i%6]:
            huollot[kohta] = st.selectbox(f"{kohta}:", ["--", "Vaihd", "Tark", "OK", "Muu"], key=f"valinta_{kohta}")

    if st.button("Tallenna huolto"):
        if not kone_nimi or not ryhma or not tunnit:
            st.warning("Täytä kaikki kentät!")
        else:
            uusi = {
                "Kone": kone_nimi,
                "Ryhmä": ryhma,
                "Tunnit": tunnit,
                "Päivämäärä": pvm.strftime("%d.%m.%Y"),
                "Vapaa teksti": vapaa,
            }
            for kohta in huoltokohteet:
                uusi[kohta] = huollot[kohta]
            uusi_df = pd.DataFrame([uusi])
            uusi_df = pd.concat([df, uusi_df], ignore_index=True)
            tallenna_data_gsheet(uusi_df)
            st.success("Huolto tallennettu!")
            st.rerun()

# --- Huoltohistoria ---
with tab2:
    st.header("Huoltohistoria (pysyvä)")
    if df.empty:
        st.info("Ei huoltoja tallennettu vielä.")
    else:
        st.dataframe(df, hide_index=True)
        if st.button("Lataa PDF"):
            pdf_naytto = df.copy()
            def pdf_footer(canvas, doc):
                canvas.saveState()
                canvas.setFont('Helvetica', 8)
                canvas.drawCentredString(420, 20, f"Sivu {doc.page}")
                canvas.restoreState()
            otsikkotyyli = ParagraphStyle(
                name='OtsikkoIso',
                fontName='Helvetica-Bold',
                fontSize=16,
                leading=22,
                alignment=0
            )
            otsikko = Paragraph("Huoltohistoria", otsikkotyyli)
            paivays = Paragraph(datetime.today().strftime("%d.%m.%Y"), getSampleStyleSheet()["Normal"])
            otsikko_paivays_table = Table(
                [[otsikko, paivays]],
                colWidths=[380, 200]
            )
            otsikko_paivays_table.setStyle(TableStyle([
                ("ALIGN", (0,0), (0,0), "LEFT"),
                ("ALIGN", (1,0), (1,0), "RIGHT"),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("BOTTOMPADDING", (0,0), (-1,-1), 0),
                ("TOPPADDING", (0,0), (-1,-1), 0),
            ]))
            kone_bold = ParagraphStyle("BoldKone", fontName="Helvetica-Bold", fontSize=8, alignment=0)
            normal_style = ParagraphStyle("Normaali", fontName="Helvetica", fontSize=8, alignment=0)
            data = [list(pdf_naytto.columns)]
            green_cells = []
            for i, (_, row) in enumerate(pdf_naytto.iterrows(), start=1):
                pdf_row = []
                for j, col in enumerate(pdf_naytto.columns):
                    value = row[col]
                    if col == "Kone" and value and not value.isdigit() and not value.strip().isdigit():
                        pdf_row.append(Paragraph(str(value), kone_bold))
                    elif str(value).strip().lower() in ["ok", "✅", "✓"]:
                        pdf_row.append("\u2713")
                        green_cells.append((j, len(data)))
                    else:
                        pdf_row.append(str(value))
                data.append(pdf_row)
            pdf_col_widths = [110, 80, 60, 80, 140] + [30] * (len(pdf_naytto.columns) - 5)
            table = Table(data, colWidths=pdf_col_widths, repeatRows=1)
            ts = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#51c987")),
                ('ALIGN',(0,0),(-1,-1),'CENTER'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('FONTSIZE', (0,0), (-1,-1), 8)
            ])
            for i in range(1, len(data)):
                if i % 2 == 1:
                    ts.add('BACKGROUND', (0,i), (-1,i), colors.whitesmoke)
            for (j,i) in green_cells:
                ts.add('TEXTCOLOR', (j,i), (j,i), colors.green)
            table.setStyle(ts)
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer, pagesize=landscape(A4),
                topMargin=35, leftMargin=40, rightMargin=40, bottomMargin=35
            )
            elements = [
                Spacer(1, 4*mm),
                otsikko_paivays_table,
                Spacer(1, 4*mm),
                table
            ]
            doc.build(elements, onFirstPage=pdf_footer, onLaterPages=pdf_footer)
            buffer.seek(0)
            st.download_button(
                label="Lataa PDF-tiedosto",
                data=buffer,
                file_name="huoltohistoria.pdf",
                mime="application/pdf"
            )
