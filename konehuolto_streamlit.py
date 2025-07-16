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
import base64
import uuid

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

# --- Taustakuva ---
def taustakuva_local(filename):
    try:
        with open(filename, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()
        return f"data:image/jpg;base64,{encoded}"
    except:
        return ""

kuva_base64 = taustakuva_local("tausta.png")

st.set_page_config(page_title="Konehuolto", layout="wide")
st.markdown("""
    <style>
    .block-container {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown(
    f"""
    <div style="
        background-image: url('{kuva_base64}');
        background-size: cover;
        background-position: center;
        padding: 80px 0 80px 0;
        margin-bottom: 0.2em;
        text-align: center;
        width: 100vw;
        position: relative;
        left: 50%;
        right: 50%;
        margin-left: -50vw;
        margin-right: -50vw;
    ">
        <h2 style="color:#fff; text-shadow:2px 2px 6px #333;">Konehuolto-ohjelma (selainversio)</h2>
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown("---")

# --- Google Sheets API ---
def get_gsheet_connection(tabname):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open(st.secrets["SHEET_NIMI"])
    return sheet.worksheet(tabname)

def lue_huollot():
    ws = get_gsheet_connection("Huollot")
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    # Täydennä pakolliset kentät, jos puuttuu
    pakolliset = [
        "ID", "Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti", "Moottoriöljy", "Hydrauliöljy", "Akseliöljy", "Ilmansuodatin",
        "Moottoriöljyn suodatin", "Hydrauli suodatin", "Rasvaus", "Polttoaine suodatin", "Tulpat", "Vaihdelaatikko öljy", "Peräöljy"
    ]
    for kentta in pakolliset:
        if kentta not in df.columns:
            df[kentta] = ""
    return df

def tallenna_huollot(df):
    ws = get_gsheet_connection("Huollot")
    ws.clear()
    if not df.empty:
        ws.update([df.columns.values.tolist()] + df.values.tolist())

def lue_koneet():
    ws = get_gsheet_connection("Koneet")
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    for kentta in ["Kone", "ID", "Ryhmä"]:
        if kentta not in df.columns:
            df[kentta] = ""
    return df

def tallenna_koneet(df):
    ws = get_gsheet_connection("Koneet")
    ws.clear()
    if not df.empty:
        ws.update([df.columns.values.tolist()] + df.values.tolist())

def ryhmat_ja_koneet(df):
    d = {}
    for _, r in df.iterrows():
        d.setdefault(r["Ryhmä"], []).append({"nimi": r["Kone"], "id": r["ID"]})
    return d

try:
    huolto_df = lue_huollot()
except Exception as e:
    st.error("Huoltojen Google Sheet puuttuu tai ei lukuoikeuksia.")
    huolto_df = pd.DataFrame()

try:
    koneet_df = lue_koneet()
except Exception as e:
    st.error("Koneiden Google Sheet puuttuu tai ei lukuoikeuksia.")
    koneet_df = pd.DataFrame()

koneet_data = ryhmat_ja_koneet(koneet_df) if not koneet_df.empty else {}

tab1, tab2, tab3 = st.tabs(["➕ Lisää huolto", "📋 Huoltohistoria", "🛠 Koneet ja ryhmät"])

with tab1:
    st.header("Lisää uusi huoltotapahtuma")
    ryhmat_lista = sorted(list(koneet_data.keys()))
    valittu_ryhma = st.selectbox("Ryhmä", ryhmat_lista, key="ryhma_selectbox")
    koneet_ryhmaan = koneet_data[valittu_ryhma] if valittu_ryhma else []
    if koneet_ryhmaan:
        koneet_df2 = pd.DataFrame(koneet_ryhmaan)
        koneet_df2["valinta"] = koneet_df2["nimi"] + " (ID: " + koneet_df2["id"].astype(str) + ")"
        kone_valinta = st.radio(
            "Valitse kone:",
            koneet_df2["valinta"].tolist(),
            key="konevalinta_radio",
            index=0 if len(koneet_df2) > 0 else None
        )
        valittu_kone_nimi = kone_valinta.split(" (ID:")[0]
        kone_id = koneet_df2[koneet_df2["nimi"] == valittu_kone_nimi]["id"].values[0]
    else:
        st.info("Valitussa ryhmässä ei ole koneita.")
        kone_id = ""
        valittu_kone_nimi = ""
    if kone_id:
        col1, col2 = st.columns(2)
        with col1:
            kayttotunnit = st.text_input("Tunnit/km", key="kayttotunnit")
        with col2:
            pvm = st.date_input("Päivämäärä", value=datetime.today(), key="pvm")
        st.markdown("#### Huoltokohteet")
        huolto_kohteet = [
            "Moottoriöljy", "Hydrauliöljy", "Akseliöljy", "Ilmansuodatin",
            "Moottoriöljyn suodatin", "Hydrauli suodatin", "Rasvaus", "Polttoaine suodatin",
            "Tulpat", "Vaihdelaatikko öljy", "Peräöljy"
        ]
        vaihtoehdot = ["--", "Vaihd", "Tark", "OK", "Muu"]
        valinnat = {}
        cols_huolto = st.columns(6)
        for i, kohta in enumerate(huolto_kohteet):
            with cols_huolto[i % 6]:
                valinnat[kohta] = st.selectbox(
                    f"{kohta}:", vaihtoehdot,
                    key=f"valinta_{kohta}",
                    index=0
                )
        vapaa = st.text_input("Vapaa teksti", key="vapaa")
        if st.button("Tallenna huolto"):
            if not valittu_ryhma or not valittu_kone_nimi or not kayttotunnit or not kone_id:
                st.warning("Täytä kaikki kentät!")
            else:
                uusi = {
                    "ID": str(uuid.uuid4())[:8],
                    "Kone": valittu_kone_nimi,
                    "Ryhmä": valittu_ryhma,
                    "Tunnit": kayttotunnit,
                    "Päivämäärä": pvm.strftime("%d.%m.%Y"),
                    "Vapaa teksti": vapaa,
                }
                for kohta in huolto_kohteet:
                    uusi[kohta] = valinnat[kohta]
                uusi_df = pd.DataFrame([uusi])
                yhdistetty = pd.concat([huolto_df, uusi_df], ignore_index=True)
                tallenna_huollot(yhdistetty)
                st.success("Huolto tallennettu!")
                st.rerun()

with tab2:
    st.header("Huoltohistoria")
    if huolto_df.empty:
        st.info("Ei huoltoja tallennettu vielä.")
    else:
        df = huolto_df.copy()
        df = df.reset_index(drop=True)
        st.dataframe(df, hide_index=True)
        muokattava_id = st.selectbox("Valitse muokattava huolto", [""] + df["ID"].astype(str).tolist())
        if muokattava_id:
            valittu = df[df["ID"].astype(str) == muokattava_id].iloc[0]
            uusi_tunnit = st.text_input("Tunnit/km", value=valittu.get("Tunnit", ""))
            uusi_pvm = st.text_input("Päivämäärä", value=valittu.get("Päivämäärä", ""))
            uusi_vapaa = st.text_input("Vapaa teksti", value=valittu.get("Vapaa teksti", ""))
            uusi_kohta = {}
            for kohta in [
                "Moottoriöljy", "Hydrauliöljy", "Akseliöljy", "Ilmansuodatin",
                "Moottoriöljyn suodatin", "Hydrauli suodatin", "Rasvaus", "Polttoaine suodatin",
                "Tulpat", "Vaihdelaatikko öljy", "Peräöljy"
            ]:
                uusi_kohta[kohta] = st.selectbox(
                    kohta, ["--", "Vaihd", "Tark", "OK", "Muu"], index=["--", "Vaihd", "Tark", "OK", "Muu"].index(valittu.get(kohta, "--")), key=f"edit_{kohta}"
                )
            if st.button("Tallenna muutokset"):
                idx = df[df["ID"].astype(str) == muokattava_id].index[0]
                df.at[idx, "Tunnit"] = uusi_tunnit
                df.at[idx, "Päivämäärä"] = uusi_pvm
                df.at[idx, "Vapaa teksti"] = uusi_vapaa
                for kohta in uusi_kohta:
                    df.at[idx, kohta] = uusi_kohta[kohta]
                tallenna_huollot(df)
                st.success("Tallennettu!")
                st.rerun()
            if st.button("Poista tämä huolto"):
                df = df[df["ID"].astype(str) != muokattava_id]
                tallenna_huollot(df)
                st.success("Huolto poistettu!")
                st.rerun()
        st.markdown("#### Lataa huoltohistoria PDF-tiedostona")
        if st.button("Lataa PDF"):
            st.info("PDF-lataus toimii kuten ennen! (Voit lisätä PDF-koodin tähän.)")
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

def tee_pdf_data(df):
    LYHENTEET = ["MÖ", "HÖ", "AÖ", "IS", "MS", "HS", "R", "PS", "T", "VÖ", "PÖ"]
    otsikot = ["Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
    data = [otsikot]
    koneet = df["Kone"].unique()
    for kone in koneet:
        r_kone = df[df["Kone"] == kone]
        eka = True
        for idx, row in r_kone.iterrows():
            rivi = [
                kone if eka else (row["ID"] if not eka else ""),
                row.get("Ryhmä", ""),
                row.get("Tunnit", ""),
                row.get("Päivämäärä", ""),
                row.get("Vapaa teksti", ""),
            ] + [row.get(k, "") for k in LYHENTEET]
            rivi = [("✔" if v == "OK" else v) for v in rivi]
            data.append(rivi)
            eka = False
        # Koneen jälkeen lyhennerivi
        data.append([""] * (len(otsikot) - len(LYHENTEET)) + LYHENTEET)
    return data

def lataa_pdf(df):
    buffer = BytesIO()
    vihrea = ParagraphStyle(name="vihrea", textColor=colors.green, fontName="Helvetica-Bold", fontSize=8)
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=0.5 * inch, leftMargin=0.5 * inch,
        topMargin=0.7 * inch, bottomMargin=0.5 * inch
    )
    data = tee_pdf_data(df)
    def pdf_rivi(rivi):
        uusi = []
        for cell in rivi:
            if str(cell) == "✔":
                uusi.append(Paragraph('<font color="green">✔</font>', vihrea))
            else:
                uusi.append(str(cell) if cell is not None else "")
        return uusi
    table_data = [data[0]] + [pdf_rivi(r) for r in data[1:]]
    table = Table(table_data, repeatRows=1)
    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.teal),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    # Koneen nimi boldina (PDF) jos molemmassa ekasarakkeessa sisältöä
    for r_idx, row in enumerate(table_data[1:], start=1):
        if str(row[0]).strip() and str(row[1]).strip():
            table_styles.append(('FONTNAME', (0, r_idx), (0, r_idx), 'Helvetica-Bold'))
    table.setStyle(TableStyle(table_styles))
    doc.build([table])
    buffer.seek(0)
    return buffer

# Lisää tämä "Huoltohistoria" tab2-osioon (esim. dataframe-näytön ja muokkauslomakkeen jälkeen):
if st.button("Lataa PDF"):
    pdfdata = lataa_pdf(df)
    st.download_button(
        label="Lataa PDF-tiedosto",
        data=pdfdata,
        file_name="huoltohistoria.pdf",
        mime="application/pdf"
    )

            

with tab3:
    st.header("Koneiden ja ryhmien hallinta")
    uusi_ryhma = st.selectbox("Ryhmän valinta tai luonti", list(koneet_data.keys())+["Uusi ryhmä"], key="uusi_ryhma")
    kaytettava_ryhma = st.text_input("Uuden ryhmän nimi") if uusi_ryhma=="Uusi ryhmä" else uusi_ryhma
    uusi_nimi = st.text_input("Koneen nimi")
    uusi_id = st.text_input("Koneen ID-numero")
    if st.button("Lisää kone"):
        if kaytettava_ryhma and uusi_nimi and uusi_id:
            uusi = pd.DataFrame([{"Kone": uusi_nimi, "ID": uusi_id, "Ryhmä": kaytettava_ryhma}])
            uusi_koneet_df = pd.concat([koneet_df, uusi], ignore_index=True)
            tallenna_koneet(uusi_koneet_df)
            st.success(f"Kone {uusi_nimi} lisätty ryhmään {kaytettava_ryhma}")
            st.rerun()
        else:
            st.warning("Täytä kaikki kentät.")

    st.subheader("Poista kone")
    if not koneet_df.empty:
        poisto_ryhma = st.selectbox("Valitse ryhmä (poistoa varten)", list(koneet_data.keys()), key="poistoryhma")
        koneet_poisto = koneet_df[koneet_df["Ryhmä"] == poisto_ryhma]
        if not koneet_poisto.empty:
            poisto_nimi = st.selectbox("Valitse kone", koneet_poisto["Kone"].tolist(), key="poistokone")
            if st.button("Poista kone"):
                uusi_koneet_df = koneet_df[~((koneet_df["Ryhmä"] == poisto_ryhma) & (koneet_df["Kone"] == poisto_nimi))]
                tallenna_koneet(uusi_koneet_df)
                st.success(f"Kone {poisto_nimi} poistettu.")
                st.rerun()
        else:
            st.info("Valitussa ryhmässä ei koneita.")
    else:
        st.info("Ei ryhmiä.")

    st.markdown("---")
    st.subheader("Ryhmän koneet")
    if not koneet_df.empty:
        ryhma_valinta = st.selectbox("Näytä koneet ryhmästä", list(koneet_data.keys()), key="ryhmat_lista_nakyma")
        koneet_listattavaan = koneet_df[koneet_df["Ryhmä"] == ryhma_valinta]
        if not koneet_listattavaan.empty:
            koneet_df_nakyma = koneet_listattavaan[["Kone", "ID"]]
            st.table(koneet_df_nakyma)
        else:
            st.info("Ryhmässä ei koneita.")
    else:
        st.info("Ei ryhmiä.")
