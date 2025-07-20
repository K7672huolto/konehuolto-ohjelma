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
        d.setdefault(r["Ryhmä"], []).append({"nimi": r["Kone"], "id": r["ID"]})
    return d

huolto_df = lue_huollot()
koneet_df = lue_koneet()
koneet_data = ryhmat_ja_koneet(koneet_df) if not koneet_df.empty else {}

tab1, tab2, tab3 = st.tabs(["➕ Lisää huolto", "📋 Huoltohistoria", "🛠 Koneet ja ryhmät"])

with tab1:
    st.header("Lisää uusi huoltotapahtuma")
    ryhmat_lista = sorted(list(koneet_data.keys()))
    if not ryhmat_lista:
        st.info("Ei yhtään koneryhmää vielä. Lisää koneita välilehdellä 'Koneet ja ryhmät'.")
    else:
        valittu_ryhma = st.selectbox("Ryhmä", ryhmat_lista, key="ryhma_selectbox")
        koneet_ryhmaan = koneet_data.get(valittu_ryhma, [])

        if koneet_ryhmaan:
            koneet_df2 = pd.DataFrame(koneet_ryhmaan)
            st.write("DEBUG: koneet_df2.columns:", koneet_df2.columns.tolist())

            # Etsi koneen nimi- ja ID-sarake
            if "Kone" in koneet_df2.columns:
                kone_sarake = "Kone"
            elif "nimi" in koneet_df2.columns:
                kone_sarake = "nimi"
            else:
                st.error("Sheetissä ei saraketta 'Kone' tai 'nimi'. Nykyiset sarakkeet: " + str(list(koneet_df2.columns)))
                st.stop()

            if "ID" in koneet_df2.columns:
                id_sarake = "ID"
            elif "id" in koneet_df2.columns:
                id_sarake = "id"
            else:
                st.error("Sheetissä ei saraketta 'ID' tai 'id'. Nykyiset sarakkeet: " + str(list(koneet_df2.columns)))
                st.stop()

            koneet_df2[kone_sarake] = koneet_df2[kone_sarake].fillna("Tuntematon kone")
            kone_valinta = st.radio(
                "Valitse kone:",
                koneet_df2[kone_sarake].tolist(),
                key="konevalinta_radio",
                index=0 if len(koneet_df2) > 0 else None
            )
            kone_id = koneet_df2[koneet_df2[kone_sarake] == kone_valinta][id_sarake].values
            kone_id = kone_id[0] if len(kone_id) > 0 else ""
        else:
            st.info("Valitussa ryhmässä ei ole koneita.")
            kone_id = ""
            kone_valinta = ""

        if kone_id:
            col1, col2 = st.columns(2)
            with col1:
                kayttotunnit = st.text_input("Tunnit/km", key="kayttotunnit")
            with col2:
                pvm = st.date_input("Päivämäärä", value=datetime.today(), key="pvm")
            st.markdown("#### Huoltokohteet")
            vaihtoehdot = ["--", "Vaihd", "Tark", "OK", "Muu"]
            valinnat = {}
            cols_huolto = st.columns(6)
            for i, pitkä in enumerate(HUOLTOKOHTEET):
                with cols_huolto[i % 6]:
                    valinnat[HUOLTOKOHTEET[pitkä]] = st.selectbox(
                        f"{pitkä}:", vaihtoehdot,
                        key=f"valinta_{pitkä}",
                        index=0
                    )
            vapaa = st.text_input("Vapaa teksti", key="vapaa")
            if st.button("Tallenna huolto", key="tallenna_huolto_tab1"):
                # Nyt TARKISTETAAN VAIN pakolliset
                if not valittu_ryhma or not kone_valinta or not kayttotunnit or not kone_id:
                    st.warning("Täytä ryhmä, kone, tunnit ja päivämäärä!")
                else:
                    uusi = {
                        "ID": str(uuid.uuid4())[:8],
                        "Kone": kone_valinta,
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
                    yhdistetty = yhdistetty.fillna("")  # Poista NaN
                    yhdistetty = yhdistetty.astype(str) # Kaikki stringiksi
                    st.write("TALLENNETTAVAT SARAKKEET:", yhdistetty.columns.tolist())
                    st.write("TALLENNETTAVAT DATA:", yhdistetty.head(3).to_dict())
                    tallenna_huollot(yhdistetty)
                    st.success("Huolto tallennettu!")
                    st.rerun()



# --- Huoltohistoria + Muokkaus + PDF ---
with tab2:
    st.header("Huoltohistoria")
    # ... kaikki suodatuslogiikka ja esikatselu_df kuten aiemmin ...
    df_naytto = esikatselu_df(df)
    st.dataframe(df_naytto, hide_index=True)

    if st.button("Lataa PDF", key="pdfhistoria"):
        pdfdata = lataa_pdf(df_naytto)
        st.download_button(
            label="Lataa PDF-tiedosto",
            data=pdfdata,
            file_name="huoltohistoria.pdf",
            mime="application/pdf"
        )


    # Suodatus ryhmän ja koneen mukaan
    ryhmat_lista = sorted(list(koneet_data.keys()))
    valittu_ryhma = st.selectbox("Suodata ryhmän mukaan", ["Kaikki"] + ryhmat_lista, key="hist_ryhma")
    if valittu_ryhma == "Kaikki":
        filtered_df = huolto_df.copy()
    else:
        filtered_df = huolto_df[huolto_df["Ryhmä"] == valittu_ryhma]

    koneet_lista = sorted(filtered_df["Kone"].dropna().unique())
    valittu_kone = st.selectbox("Suodata koneen mukaan", ["Kaikki"] + koneet_lista, key="hist_kone")
    if valittu_kone == "Kaikki":
        df = filtered_df.copy()
    else:
        df = filtered_df[filtered_df["Kone"] == valittu_kone]

    # --------- Esikatselu DataFrame ---------
    def esikatselu_df(df):
        rows = []
        viime_kone = None
        for idx, row in df.iterrows():
            kone = row.get("Kone", "")
            kone_id = row.get("ID-numero", "")
            if kone != viime_kone:
                if viime_kone is not None:
                    rows.append([""] * (5 + len(LYHENTEET)))
                # Koneen nimi -rivi
                rows.append([
                    kone,
                    row.get("Ryhmä", ""),
                    row.get("Tunnit", ""),
                    row.get("Päivämäärä", ""),
                    row.get("Vapaa teksti", ""),
                    *[("✔" if str(row.get(k, "")).strip().upper() == "OK" else row.get(k, "")) for k in LYHENTEET]
                ])
                # Koneen ID -rivi (sarakkeessa 1, muut tyhjiä)
                rows.append([
                    kone_id,
                    "", "", "", "",
                    *["" for k in LYHENTEET]
                ])
            else:
                rows.append([
                    "",
                    row.get("Ryhmä", ""),
                    row.get("Tunnit", ""),
                    row.get("Päivämäärä", ""),
                    row.get("Vapaa teksti", ""),
                    *[("✔" if str(row.get(k, "")).strip().upper() == "OK" else row.get(k, "")) for k in LYHENTEET]
                ])
            viime_kone = kone
        columns = ["Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
        return pd.DataFrame(rows, columns=columns)

    df_naytto = esikatselu_df(df)
    st.dataframe(df_naytto, hide_index=True)

    # --------- PDF-latausnappi ---------
    def lataa_pdf(df):
        buffer = BytesIO()
        vihrea = ParagraphStyle(name="vihrea", textColor=colors.green, fontName="Helvetica-Bold", fontSize=8)
        # Data
        data = [df.columns.tolist()] + df.values.tolist()

        def pdf_rivi(rivi):
            uusi = []
            for cell in rivi:
                if str(cell).strip() == "✔":
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

        # --- Otsikko, päiväys ja sivunumero joka sivulle ---
        def pdf_header_footer(canvas, doc):
            canvas.saveState()
            # Otsikko vasempaan yläkulmaan
            canvas.setFont('Helvetica-Bold', 16)
            canvas.drawString(40, A4[1] - 40, "Huoltohistoria")
            # Päivämäärä oikeaan yläkulmaan
            canvas.setFont('Helvetica', 10)
            canvas.drawString(640, A4[1] - 35, datetime.today().strftime("%d.%m.%Y"))
            # Sivunumero alas keskelle
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(420, 20, f"Sivu {doc.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            topMargin=50, leftMargin=40, rightMargin=40, bottomMargin=35
        )
        elements = [table]
        doc.build(elements,
            onFirstPage=pdf_header_footer,
            onLaterPages=pdf_header_footer
        )
        buffer.seek(0)
        return buffer


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
