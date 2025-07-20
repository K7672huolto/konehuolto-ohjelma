import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
import base64
import uuid






# --- Kirjautuminen ---
import streamlit as st

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


# --- Taustakuva (banneri) ---
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
        padding: 90px 0 90px 0;
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

# --- Huoltokohteet
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
    pakolliset = ["ID", "Kone", "ID-numero", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
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
        st.write("DEBUG DATA:", data)
        df = pd.DataFrame(data)
        st.write("DEBUG COLUMNS:", df.columns)
        return df
    except Exception as e:
        st.error(f"VIRHE KONEET LUKU: {e}")
        return pd.DataFrame()


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

# Lataa data Sheetistä
huolto_df = lue_huollot()
koneet_df = lue_koneet()
koneet_data = ryhmat_ja_koneet(koneet_df) if not koneet_df.empty else {}

# Lomakkeen resetointi
if "lomake_reset" not in st.session_state:
    st.session_state.lomake_reset = 0

tab1, tab2, tab3 = st.tabs(["➕ Lisää huolto", "📋 Huoltohistoria", "🛠 Koneet ja ryhmät"])

### --- TAB1: Lisää huolto
with tab1:
    st.header("Lisää uusi huoltotapahtuma")
    ryhmat_lista = sorted(list(koneet_data.keys()))
    if not ryhmat_lista:
        st.info("Ei yhtään koneryhmää vielä. Lisää koneita välilehdellä 'Koneet ja ryhmät'.")
    else:
        valittu_ryhma = st.selectbox("Ryhmä", ryhmat_lista, key="ryhma_selectbox"+str(st.session_state.lomake_reset))
        koneet_ryhmaan = koneet_data[valittu_ryhma] if valittu_ryhma else []
        if koneet_ryhmaan:
            koneet_df2 = pd.DataFrame(koneet_ryhmaan)
            koneet_df2["valinta"] = koneet_df2["nimi"] + " (ID: " + koneet_df2["id"].astype(str) + ")"
            kone_valinta = st.radio(
                "Valitse kone:",
                koneet_df2["valinta"].tolist(),
                key="konevalinta_radio"+str(st.session_state.lomake_reset),
                index=0 if len(koneet_df2) > 0 else None
            )
            valittu_kone_nimi = kone_valinta.split(" (ID:")[0]
            kone_id = koneet_df2[koneet_df2["valinta"] == kone_valinta]["id"].values[0]
        else:
            st.info("Valitussa ryhmässä ei ole koneita.")
            kone_id = ""
            valittu_kone_nimi = ""

        if kone_id:
            col1, col2 = st.columns(2)
            with col1:
                kayttotunnit = st.text_input("Tunnit/km", key="kayttotunnit"+str(st.session_state.lomake_reset))
            with col2:
                pvm = st.date_input("Päivämäärä", value=datetime.today(), key="pvm"+str(st.session_state.lomake_reset))
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
            vapaa = st.text_input("Vapaa teksti", key="vapaa"+str(st.session_state.lomake_reset))
            if st.button("Tallenna huolto", key="tallenna_huolto_tab1"):
                if not valittu_ryhma or not valittu_kone_nimi or not kayttotunnit or not kone_id:
                    st.warning("Täytä kaikki kentät!")
                else:
                    uusi = {
                        "ID": str(uuid.uuid4())[:8],
                        "Kone": valittu_kone_nimi,
                        "ID-numero": kone_id,
                        "Ryhmä": valittu_ryhma,
                        "Tunnit": kayttotunnit,
                        "Päivämäärä": pvm.strftime("%d.%m.%Y"),
                        "Vapaa teksti": vapaa,
                    }
                    for lyhenne in LYHENTEET:
                        uusi[lyhenne] = valinnat[lyhenne]
                    uusi_df = pd.DataFrame([uusi])
                    yhdistetty = pd.concat([huolto_df, uusi_df], ignore_index=True)
                    tallenna_huollot(yhdistetty)
                    st.success("Huolto tallennettu!")
                    st.session_state.lomake_reset += 1
                    st.experimental_rerun()

### --- TAB2: Huoltohistoria ja PDF
with tab2:
    st.header("Huoltohistoria")

    # 1. Ryhmävalinta (myös "Kaikki")
    ryhmat_lista = sorted(list(koneet_data.keys()))
    valittu_ryhma = st.selectbox("Suodata ryhmän mukaan", ["Kaikki"] + ryhmat_lista, key="hist_ryhma")
    if valittu_ryhma == "Kaikki":
        df_suodatettu = huolto_df.copy()
    else:
        df_suodatettu = huolto_df[huolto_df["Ryhmä"] == valittu_ryhma]

    # 2. Konevalinta (myös "Kaikki")
    koneet_lista = df_suodatettu["Kone"].dropna().unique().tolist()
    valittu_kone = st.selectbox("Suodata koneen mukaan", ["Kaikki"] + koneet_lista, key="hist_kone")
    if valittu_kone == "Kaikki":
        df = df_suodatettu.copy()
    else:
        df = df_suodatettu[df_suodatettu["Kone"] == valittu_kone]

    # 3. Esikatselun rakentaminen (vihreä ✔ myös esikatseluun)
    def fmt_ok(x):
        return "✔" if str(x).strip().upper() == "OK" else x

    def esikatselu_df(df):
        rows = []
        rivinro = 1
        viime_kone = None
        for idx, row in df.iterrows():
            kone = row.get("Kone", "")
            kone_id = row.get("ID-numero", "")
            ryhma = row.get("Ryhmä", "")
            tunnit = row.get("Tunnit", "")
            pvm = row.get("Päivämäärä", "")
            vapaa = row.get("Vapaa teksti", "")
            huoltodata = [fmt_ok(row.get(k, "")) for k in LYHENTEET]

            if kone != viime_kone and viime_kone is not None:
                rows.append([""] * (6 + len(LYHENTEET)))
                rivinro += 1

            # 1. rivi: koneen nimi, ryhmä, tunnit, pvm, vapaa, huollot
            rows.append([rivinro, kone, ryhma, tunnit, pvm, vapaa, *huoltodata])
            rivinro += 1
            # 2. rivi: ID, muut tyhjiä, huollot
            rows.append([rivinro, kone_id, "", "", "", "", *huoltodata])
            rivinro += 1
            viime_kone = kone

        columns = ["Rivi", "Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
        return pd.DataFrame(rows, columns=columns)

    df_naytto = esikatselu_df(df)
    st.dataframe(df_naytto, hide_index=True)

    # 4. PDF-nappi (vihreä ✔ myös PDF:ään)
    def lataa_pdf(df):
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib import colors
        from reportlab.lib.units import mm

        buffer = BytesIO()
        otsikkotyyli = ParagraphStyle(
            name='OtsikkoIso', fontName='Helvetica-Bold', fontSize=16, leading=22, alignment=0
        )
        otsikko = Paragraph("Huoltohistoria", otsikkotyyli)
        paivays = Paragraph(datetime.today().strftime("%d.%m.%Y"), ParagraphStyle(name="Norm", fontSize=10, alignment=2))
        otsikko_paivays_table = Table(
            [[otsikko, paivays]], colWidths=[380, 200]
        )
        vihrea = ParagraphStyle(name="vihrea", textColor=colors.green, fontName="Helvetica-Bold", fontSize=8)
        normaali = ParagraphStyle("Normaali", fontName="Helvetica", fontSize=8, alignment=0)

        data = [df.columns.tolist()]
        for _, row in df.iterrows():
            pdf_row = []
            for j, col in enumerate(df.columns):
                value = row[col]
                if str(value).strip() == "✔":
                    pdf_row.append(Paragraph('<font color="green">✔</font>', vihrea))
                else:
                    pdf_row.append(str(value))
            data.append(pdf_row)

        sarakeleveys = [32, 110, 90, 55, 70, 110] + [32] * (len(df.columns) - 6)
        table = Table(data, colWidths=sarakeleveys, repeatRows=1)
        ts = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#51c987")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ])
        for i in range(1, len(data)):
            if i % 2 == 1:
                ts.add('BACKGROUND', (0, i), (-1, i), colors.whitesmoke)
        table.setStyle(ts)

        def pdf_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(420, 20, f"Sivu {doc.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            topMargin=35, leftMargin=40, rightMargin=40, bottomMargin=35
        )
        elements = [
            Spacer(1, 12),
            otsikko_paivays_table,
            Spacer(1, 12),
            table
        ]
        doc.build(elements, onFirstPage=pdf_footer, onLaterPages=pdf_footer)
        buffer.seek(0)
        return buffer

    st.markdown("#### Lataa huoltohistoria PDF-tiedostona")
    if st.button("Lataa PDF", key="lataa_pdf_nappi"):
        pdfdata = lataa_pdf(df_naytto)
        st.download_button(
            label="Lataa PDF-tiedosto",
            data=pdfdata,
            file_name="huoltohistoria.pdf",
            mime="application/pdf"
        )



# --- Koneiden ja ryhmien hallinta ---
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
