import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm, inch
import base64
import uuid
import streamlit as st

# Kirjautumistila: aseta oletus
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "login_failed" not in st.session_state:
    st.session_state["login_failed"] = False

def login():
    st.title("Kirjaudu sisään")
    username = st.text_input("Käyttäjätunnus", key="user_login")
    password = st.text_input("Salasana", type="password", key="pw_login")
    if st.button("Kirjaudu"):
        if username == "mattipa" and password == "jdtoro#":
            st.session_state["logged_in"] = True
            st.session_state["login_failed"] = False
        else:
            st.session_state["login_failed"] = True

if not st.session_state["logged_in"]:
    login()
    if st.session_state["login_failed"]:
        st.error("Väärä käyttäjätunnus tai salasana.")
    st.stop()
# Kirjautuminen
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("Kirjaudu sisään")
    username = st.text_input("Käyttäjätunnus", key="user_login")
    password = st.text_input("Salasana", type="password", key="pw_login")
    login_attempt = st.button("Kirjaudu")
    if login_attempt:
        if username == "mattipa" and password == "jdtoro#":
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.session_state.login_failed = True

if not st.session_state.logged_in:
    login()
    if st.session_state.get("login_failed", False):
        st.error("Väärä käyttäjätunnus tai salasana.")
    st.stop()

# Taustakuva (banneri)
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

# Huoltokohteet
HUOLTOKOHTEET = {
    "Moottoriöljy": "MÖ",
    "Hydrauliöljy": "HÖ",
    "Akseliöljy": "AÖ",
    "Ilmansuodatin": "IS",
    "Moottoriöljyn suodatin": "MS",
    "Hydrauli suodatin": "HS",
    "Rasvaus": "R",
    "Polttoaine suodatin": "PS",
    "Tulpat": "T",
    "Vaihdelaatikko öljy": "VÖ",
    "Peräöljy": "PÖ"
}
LYHENTEET = list(HUOLTOKOHTEET.values())

# Google Sheets API
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
    try:
        ws = get_gsheet_connection("Huollot")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"Huoltojen Google Sheet puuttuu tai ei lukuoikeuksia. ({e})")
        df = pd.DataFrame()
    pakolliset = ["ID", "Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
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
    try:
        ws = get_gsheet_connection("Koneet")
        data = ws.get_all_records()
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"Koneiden Google Sheet puuttuu tai ei lukuoikeuksia. ({e})")
        df = pd.DataFrame()
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
        d.setdefault(r["Ryhmä"], []).append({"Kone": r["Kone"], "ID": r["ID"]})
    return d

huolto_df = lue_huollot()
koneet_df = lue_koneet()
koneet_data = ryhmat_ja_koneet(koneet_df) if not koneet_df.empty else {}

tab1, tab2, tab3 = st.tabs(["➕ Lisää huolto", "📋 Huoltohistoria", "🛠 Koneet ja ryhmät"])

# --- TAB1: Lisää huolto ---
with tab1:
    st.header("Lisää uusi huoltotapahtuma")
    ryhmat_lista = sorted(list(koneet_df["Ryhmä"].dropna().unique()))
    if not ryhmat_lista:
        st.info("Ei yhtään koneryhmää vielä. Lisää koneita välilehdellä 'Koneet ja ryhmät'.")
    else:
        valittu_ryhma = st.selectbox("Ryhmä", ryhmat_lista, key="ryhma_selectbox_tab1")
        koneet_ryhmaan = koneet_df[koneet_df["Ryhmä"] == valittu_ryhma]
        if not koneet_ryhmaan.empty:
            kone_nimet = koneet_ryhmaan["Kone"].tolist()
            valittu_kone_nimi = st.radio("Valitse kone:", kone_nimet, key="konevalinta_radio_tab1")
            kone_id = koneet_ryhmaan[koneet_ryhmaan["Kone"] == valittu_kone_nimi]["ID"].values[0]
        else:
            st.info("Valitussa ryhmässä ei ole koneita.")
            kone_id = ""
            valittu_kone_nimi = ""

        if kone_id:
            # Automaattiresetointi: laske tallennusmäärä
            if "lomake_reset" not in st.session_state:
                st.session_state.lomake_reset = 0

            col1, col2 = st.columns(2)
            with col1:
                kayttotunnit = st.text_input("Tunnit/km", key=f"kayttotunnit_{st.session_state.lomake_reset}")
            with col2:
                pvm = st.date_input("Päivämäärä", value=datetime.today(), key=f"pvm_{st.session_state.lomake_reset}")

            st.markdown("#### Huoltokohteet")
            vaihtoehdot = ["--", "Vaihd", "Tark", "OK", "Muu"]
            valinnat = {}
            cols_huolto = st.columns(6)
            for i, pitkä in enumerate(HUOLTOKOHTEET):
                with cols_huolto[i % 6]:
                    valinnat[HUOLTOKOHTEET[pitkä]] = st.selectbox(
                        f"{pitkä}:", vaihtoehdot,
                        key=f"valinta_{pitkä}_{st.session_state.lomake_reset}",
                        index=0
                    )
            vapaa = st.text_input("Vapaa teksti", key=f"vapaa_{st.session_state.lomake_reset}")

            if st.button("Tallenna huolto", key=f"tallenna_huolto_tab1_{st.session_state.lomake_reset}"):
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
                    for lyhenne in LYHENTEET:
                        uusi[lyhenne] = valinnat[lyhenne]

                    # *** KORJAUS: Tallennetaan vain oikeat sarakkeet ***
                    sallitut_sarakkeet = ["ID", "Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
                    uusi_df = pd.DataFrame([uusi])
                    for sarake in sallitut_sarakkeet:
                        if sarake not in huolto_df.columns:
                            huolto_df[sarake] = ""
                        if sarake not in uusi_df.columns:
                            uusi_df[sarake] = ""
                    yhdistetty = pd.concat([huolto_df[sallitut_sarakkeet], uusi_df[sallitut_sarakkeet]], ignore_index=True)
                    tallenna_huollot(yhdistetty)
                    st.success("Huolto tallennettu!")
                    st.session_state.lomake_reset += 1
                    st.experimental_rerun()


# --- TAB2: Huoltohistoria ---
with tab2:
    st.header("Huoltohistoria")
    if huolto_df.empty:
        st.info("Ei huoltoja tallennettu vielä.")
    else:
        df = huolto_df.copy().reset_index(drop=True)
        # Valinnat
        ryhmat = ["Kaikki"] + sorted(df["Ryhmä"].unique())
        valittu_ryhma = st.selectbox("Suodata ryhmän mukaan", ryhmat, key="tab2_ryhma")
        if valittu_ryhma == "Kaikki":
            filt = df
        else:
            filt = df[df["Ryhmä"] == valittu_ryhma]
        koneet = ["Kaikki"] + sorted(filt["Kone"].unique())
        valittu_kone = st.selectbox("Suodata koneen mukaan", koneet, key="tab2_kone")
        if valittu_kone != "Kaikki":
            filt = filt[filt["Kone"] == valittu_kone]

        # *** UUSI ESIKATSELU ***
        def fmt_ok(x):
            return "✔" if str(x).strip().upper() == "OK" else x

        def uusi_esikatselu_df(df):
            """Näytä huollot: yksi rivi per huolto ja tyhjä rivi koneiden väliin."""
            rows = []
            for kone in df["Kone"].unique():
                kone_df = df[df["Kone"] == kone]
                eka = True
                for idx, row in kone_df.iterrows():
                    rows.append(
                        [row.get("Kone", "") if eka else "",
                         row.get("Ryhmä", "") if eka else "",
                         row.get("Tunnit", ""),
                         row.get("Päivämäärä", ""),
                         row.get("Vapaa teksti", "")]
                        + [fmt_ok(row.get(k, "")) for k in LYHENTEET]
                    )
                    eka = False
                # Tyhjä rivi koneen jälkeen
                rows.append([""] * (5 + len(LYHENTEET)))
            columns = ["Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
            return pd.DataFrame(rows, columns=columns)


        def tee_pdf_data(df):
            """PDF-data: yksi rivi per huolto ja tyhjä rivi koneiden väliin."""
            rows = []
            for kone in df["Kone"].unique():
                kone_df = df[df["Kone"] == kone]
                eka = True
                for idx, row in kone_df.iterrows():
                    rows.append(
                        [row.get("Kone", "") if eka else "",
                         row.get("Ryhmä", "") if eka else "",
                         row.get("Tunnit", ""),
                         row.get("Päivämäärä", ""),
                         row.get("Vapaa teksti", "")]
                        + [fmt_ok(row.get(k, "")) for k in LYHENTEET]
                    )
                    eka = False
                # Tyhjä rivi koneen jälkeen
                rows.append([""] * (5 + len(LYHENTEET)))
            columns = ["Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
            return [columns] + rows


        def lataa_pdf(df):
            buffer = BytesIO()
            vihrea = ParagraphStyle(name="vihrea", textColor=colors.green, fontName="Helvetica-Bold", fontSize=8)
            otsikkotyyli = ParagraphStyle(name="otsikko", fontName="Helvetica-Bold", fontSize=16)
            paivays = Paragraph(datetime.today().strftime("%d.%m.%Y"), ParagraphStyle("date", fontSize=12, alignment=2))
            otsikko = Paragraph("Huoltohistoria", otsikkotyyli)

            def pdf_footer(canvas, doc):
                canvas.saveState()
                canvas.setFont('Helvetica', 8)
                canvas.drawCentredString(420, 20, f"Sivu {doc.page}")
                canvas.restoreState()

            doc = SimpleDocTemplate(
                buffer, pagesize=landscape(A4),
                rightMargin=0.5 * inch, leftMargin=0.5 * inch,
                topMargin=0.7 * inch, bottomMargin=0.5 * inch
            )
            data = tee_pdf_data(df)

            def pdf_rivi(rivi):
                uusi = []
                for cell in rivi:
                    if str(cell).strip().upper() in ["✔", "OK"]:
                        uusi.append(Paragraph('<font color="green">✔</font>', vihrea))
                    else:
                        uusi.append(str(cell) if cell is not None else "")
                return uusi

            table_data = [data[0]] + [pdf_rivi(r) for r in data[1:]]
            sarakeleveys = [110, 80, 60, 80, 140] + [32 for _ in LYHENTEET]
            table = Table(table_data, repeatRows=1, colWidths=sarakeleveys)
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
            for r_idx, row in enumerate(table_data[1:], start=1):
                if str(row[0]).strip() and str(row[1]).strip():
                    table_styles.append(('FONTNAME', (0, r_idx), (0, r_idx), 'Helvetica-Bold'))
            table.setStyle(TableStyle(table_styles))
            doc.build(
                [Spacer(1, 4 * mm), 
                 Table([[otsikko, paivays]], colWidths=[340, 340], style=[
                     ("ALIGN", (0, 0), (0, 0), "LEFT"),
                     ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                     ("VALIGN", (0,0), (-1,-1), "TOP"),
                     ("BOTTOMPADDING", (0,0), (-1,-1), 0),
                     ("TOPPADDING", (0,0), (-1,-1), 0),
                 ]),
                 Spacer(1, 4 * mm),
                 table],
                onFirstPage=pdf_footer,
                onLaterPages=pdf_footer
            )
            buffer.seek(0)
            return buffer

        if st.button("Lataa PDF", key="lataa_pdf_tab2"):
            pdfdata = lataa_pdf(df_naytto)
            st.download_button(
                label="Lataa PDF-tiedosto",
                data=pdfdata,
                file_name="huoltohistoria.pdf",
                mime="application/pdf"
            )


# --- TAB3: Koneiden ja ryhmien hallinta ---
with tab3:
    st.header("Koneiden ja ryhmien hallinta")

    # --- Lisää kone ---
    st.subheader("Lisää kone")
    ryhmat_lista = list(koneet_df["Ryhmä"].dropna().unique())
    select_ryhmat = ryhmat_lista + ["Uusi ryhmä"]
    uusi_ryhma = st.selectbox(
        "Ryhmän valinta tai luonti",
        select_ryhmat,
        key="tab3_uusi_ryhma"
    )
    kaytettava_ryhma = st.text_input("Uuden ryhmän nimi", key="tab3_uusi_ryhman_nimi") if uusi_ryhma == "Uusi ryhmä" else uusi_ryhma
    uusi_nimi = st.text_input("Koneen nimi", key="tab3_koneen_nimi")
    uusi_id = st.text_input("Koneen ID-numero", key="tab3_koneen_id")

    if st.button("Lisää kone", key="lisaa_kone_nappi"):
        if kaytettava_ryhma and uusi_nimi and uusi_id:
            uusi = pd.DataFrame([{"Kone": uusi_nimi, "ID": uusi_id, "Ryhmä": kaytettava_ryhma}])
            uusi_koneet_df = pd.concat([koneet_df, uusi], ignore_index=True)
            tallenna_koneet(uusi_koneet_df)
            st.success(f"Kone {uusi_nimi} lisätty ryhmään {kaytettava_ryhma}")
            st.session_state["tab3_uusi_ryhman_nimi"] = ""
            st.session_state["tab3_koneen_nimi"] = ""
            st.session_state["tab3_koneen_id"] = ""
            st.experimental_rerun()
        else:
            st.warning("Täytä kaikki kentät.")

    st.markdown("---")
    # --- Poista kone ---
    st.subheader("Poista kone")
    if not koneet_df.empty:
        poisto_ryhma = st.selectbox(
            "Valitse ryhmä (poistoa varten)",
            list(koneet_df["Ryhmä"].dropna().unique()),
            key="tab3_poisto_ryhma"
        )
        koneet_poisto = koneet_df[koneet_df["Ryhmä"] == poisto_ryhma]
        if not koneet_poisto.empty:
            poisto_nimi = st.selectbox("Valitse kone", koneet_poisto["Kone"].tolist(), key="tab3_poisto_kone")
            if st.button("Poista kone", key=f"poista_kone_{poisto_nimi}"):
                uusi_koneet_df = koneet_df[~((koneet_df["Ryhmä"] == poisto_ryhma) & (koneet_df["Kone"] == poisto_nimi))]
                tallenna_koneet(uusi_koneet_df)
                st.success(f"Kone {poisto_nimi} poistettu.")
                # Nollaa vain selectboxit, älä tekstikenttiä!
                st.session_state["tab3_poisto_ryhma"] = ""
                st.session_state["tab3_poisto_kone"] = ""
                st.experimental_rerun()
        else:
            st.info("Valitussa ryhmässä ei koneita.")
    else:
        st.info("Ei ryhmiä.")

    st.markdown("---")
    # --- Ryhmän koneet ---
    st.subheader("Ryhmän koneet")
    if not koneet_df.empty:
        ryhma_valinta = st.selectbox(
            "Näytä koneet ryhmästä",
            list(koneet_df["Ryhmä"].dropna().unique()),
            key="tab3_ryhmat_lista_nakyma"
        )
        koneet_listattavaan = koneet_df[koneet_df["Ryhmä"] == ryhma_valinta]
        if not koneet_listattavaan.empty:
            koneet_df_nakyma = koneet_listattavaan[["Kone", "ID"]]
            st.table(koneet_df_nakyma)
        else:
            st.info("Ryhmässä ei koneita.")
    else:
        st.info("Ei ryhmiä.")



