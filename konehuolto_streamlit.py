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
from reportlab.lib.units import inch, mm
import base64
import uuid

# --------- LOGIN -----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("Kirjaudu sisään")
    username = st.text_input("Käyttäjätunnus")
    password = st.text_input("Salasana", type="password")
    login_clicked = st.button("Kirjaudu")
    if login_clicked:
        if username == "mattipa" and password == "jdtoro#":
            st.session_state.logged_in = True
        else:
            st.error("Väärä käyttäjätunnus tai salasana.")

if not st.session_state.logged_in:
    login()
    st.stop()


# --------- TAUSTAKUVA (banneri) ----------
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
    .block-container { padding-top: 0rem !important; margin-top: 0rem !important; }
    </style>
""", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style="
        background-image: url('{kuva_base64}');
        background-size: cover;
        background-position: center;
        padding: 85px 0 85px 0;
        margin-bottom: 0.2em;
        text-align: center;
        width: 100vw;
        position: relative;
        left: 50%; right: 50%; margin-left: -50vw; margin-right: -50vw;
    ">
        <h2 style="color:#fff; text-shadow:2px 2px 6px #333;">Konehuolto-ohjelma (selainversio)</h2>
    </div>
    """,
    unsafe_allow_html=True
)
st.markdown("---")

# Huoltokohteet
# HUOLTOKOHTEET
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
    cleaned = df.fillna("").astype(str)
    if not cleaned.empty and set(["ID", "Kone", "Ryhmä"]).issubset(cleaned.columns):
        try:
            ws.clear()
            ws.update([cleaned.columns.values.tolist()] + cleaned.values.tolist())
        except Exception as e:
            st.error(f"Tallennus epäonnistui: {e}")
    elif cleaned.empty:
        # Tyhjennetään sheet mutta jätetään otsikot
        ws.clear()
        ws.update([["ID", "Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET])

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
    cleaned = df.fillna("").astype(str)
    if not cleaned.empty and set(["Kone", "ID", "Ryhmä"]).issubset(cleaned.columns):
        try:
            ws.clear()
            ws.update([cleaned.columns.values.tolist()] + cleaned.values.tolist())
        except Exception as e:
            st.error(f"Koneiden tallennus epäonnistui: {e}")
    elif cleaned.empty:
        ws.clear()
        ws.update([["Kone", "ID", "Ryhmä"]])

def ryhmat_ja_koneet(df):
    d = {}
    for _, r in df.iterrows():
        d.setdefault(r["Ryhmä"], []).append({"Kone": r["Kone"], "ID": r["ID"]})
    return d

# -------------- LOGIN esimerkki (voit vaihtaa oman loginin)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("Kirjaudu sisään")
    username = st.text_input("Käyttäjätunnus")
    password = st.text_input("Salasana", type="password")
    login_clicked = st.button("Kirjaudu")
    if login_clicked:
        if username == "mattipa" and password == "jdtoro#":
            st.session_state.logged_in = True
        else:
            st.error("Väärä käyttäjätunnus tai salasana.")

if not st.session_state.logged_in:
    login()
    st.stop()

# -------------- KÄYTTÖLOHKO, esim. HUOLTOJEN LISÄYS ----------------
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
        koneet_ryhmaan = koneet_data[valittu_ryhma] if valittu_ryhma else []
        if koneet_ryhmaan:
            koneet_df2 = pd.DataFrame(koneet_ryhmaan)
            koneet_df2["valinta"] = koneet_df2["Kone"]
            kone_valinta = st.radio(
                "Valitse kone:",
                koneet_df2["valinta"].tolist(),
                key="konevalinta_radio",
                index=0 if len(koneet_df2) > 0 else None
            )
            valittu_kone_nimi = kone_valinta
            kone_id = koneet_df2[koneet_df2["Kone"] == valittu_kone_nimi]["ID"].values[0]
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
                    try:
                        tallenna_huollot(yhdistetty)
                        st.success("Huolto tallennettu!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Tallennus epäonnistui: {e}")

# ... jatka ohjelmaa tab2, tab3 ...


# ------------------- TAB 2: HUOLTOHISTORIA -------------------
with tab2:
    st.header("Huoltohistoria")
    if huolto_df.empty:
        st.info("Ei huoltoja tallennettu vielä.")
    else:
        df = huolto_df.copy().reset_index(drop=True)

        # Suodatus
        ryhmat = ["Kaikki"] + sorted(df["Ryhmä"].unique())
        valittu_ryhma = st.selectbox("Suodata ryhmän mukaan", ryhmat, key="tab2_ryhma")
        filt = df if valittu_ryhma == "Kaikki" else df[df["Ryhmä"] == valittu_ryhma]
        koneet = ["Kaikki"] + sorted(filt["Kone"].unique())
        valittu_kone = st.selectbox("Suodata koneen mukaan", koneet, key="tab2_kone")
        filt = filt if valittu_kone == "Kaikki" else filt[filt["Kone"] == valittu_kone]

        # ✔ -logiikka
        def fmt_ok(x):
            return "✔" if str(x).strip().upper() == "OK" else x

        # Esikatselu-data
        def muodosta_esikatselu(df):
            rows = []
            prev_kone = None
            for _, row in df.iterrows():
                if prev_kone is not None and row["Kone"] != prev_kone:
                    rows.append([""] * (6 + len(LYHENTEET)))
                if row["Kone"] != prev_kone:
                    # Eka huolto: Kone ja ID
                    rows.append([
                        row.get("Kone", ""),
                        row.get("ID", ""),
                        row.get("Ryhmä", ""),
                        row.get("Tunnit", ""),
                        row.get("Päivämäärä", ""),
                        row.get("Vapaa teksti", ""),
                    ] + [fmt_ok(row.get(k, "")) for k in LYHENTEET])
                else:
                    # Muut huollot: Kone ja ID tyhjä
                    rows.append([
                        "", "", row.get("Ryhmä", ""), row.get("Tunnit", ""), row.get("Päivämäärä", ""), row.get("Vapaa teksti", "")
                    ] + [fmt_ok(row.get(k, "")) for k in LYHENTEET])
                prev_kone = row["Kone"]
            columns = ["Kone", "ID", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
            return pd.DataFrame(rows, columns=columns)

        df_naytto = muodosta_esikatselu(filt)
        st.dataframe(df_naytto, hide_index=True)

        # MUOKKAUS ja POISTO
        id_valinnat = [f"{row['Kone']} ({row['ID']})" for _, row in df.iterrows()]
        valittu_id_valinta = st.selectbox("Valitse muokattava huolto", [""] + id_valinnat, key="tab2_muokkaa_id")
        if valittu_id_valinta:
            valittu_id = valittu_id_valinta.split("(")[-1].replace(")", "")
            valittu = df[df["ID"].astype(str) == valittu_id].iloc[0]
            uusi_tunnit = st.text_input("Tunnit/km", value=valittu.get("Tunnit", ""), key="tab2_edit_tunnit")
            uusi_pvm = st.text_input("Päivämäärä", value=valittu.get("Päivämäärä", ""), key="tab2_edit_pvm")
            uusi_vapaa = st.text_input("Vapaa teksti", value=valittu.get("Vapaa teksti", ""), key="tab2_edit_vapaa")
            uusi_kohta = {}
            for pitkä, lyhenne in HUOLTOKOHTEET.items():
                vaihtoehdot = ["--", "Vaihd", "Tark", "OK", "Muu"]
                arvo = str(valittu.get(lyhenne, "--")).strip().upper()
                vaihtoehdot_upper = [v.upper() for v in vaihtoehdot]
                if arvo not in vaihtoehdot_upper:
                    arvo = "--"
                uusi_kohta[lyhenne] = st.selectbox(
                    pitkä,
                    vaihtoehdot,
                    index=vaihtoehdot_upper.index(arvo),
                    key=f"tab2_edit_{lyhenne}"
                )
            if st.button("Tallenna muutokset", key="tab2_tallenna_muokkaa"):
                idx = df[df["ID"].astype(str) == valittu_id].index[0]
                df.at[idx, "Tunnit"] = uusi_tunnit
                df.at[idx, "Päivämäärä"] = uusi_pvm
                df.at[idx, "Vapaa teksti"] = uusi_vapaa
                for lyhenne in uusi_kohta:
                    df.at[idx, lyhenne] = uusi_kohta[lyhenne]
                tallenna_huollot(df)
                st.success("Tallennettu!")
                st.experimental_rerun()
            if st.button("Poista tämä huolto", key="tab2_poista_huolto"):
                df = df[df["ID"].astype(str) != valittu_id]
                tallenna_huollot(df)
                st.success("Huolto poistettu!")
                st.experimental_rerun()

        # PDF-lataus
        def tee_pdf_data(df):
            rows = []
            prev_kone = None
            for _, row in df.iterrows():
                if prev_kone is not None and row["Kone"] != prev_kone:
                    rows.append([""] * (6 + len(LYHENTEET)))
                if row["Kone"] != prev_kone:
                    rows.append([
                        row.get("Kone", ""),
                        row.get("ID", ""),
                        row.get("Ryhmä", ""),
                        row.get("Tunnit", ""),
                        row.get("Päivämäärä", ""),
                        row.get("Vapaa teksti", ""),
                    ] + [fmt_ok(row.get(k, "")) for k in LYHENTEET])
                else:
                    rows.append([
                        "", "", row.get("Ryhmä", ""), row.get("Tunnit", ""), row.get("Päivämäärä", ""), row.get("Vapaa teksti", "")
                    ] + [fmt_ok(row.get(k, "")) for k in LYHENTEET])
                prev_kone = row["Kone"]
            columns = ["Kone", "ID", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
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
            sarakeleveys = [110, 80, 60, 80, 140, 32] + [32 for _ in LYHENTEET]
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
            pdfdata = lataa_pdf(filt)
            st.download_button(
                label="Lataa PDF-tiedosto",
                data=pdfdata,
                file_name="huoltohistoria.pdf",
                mime="application/pdf"
            )

# ------------------- TAB 3: KONEET JA RYHMÄT -------------------
with tab3:
    st.header("Koneiden ja ryhmien hallinta")
    uusi_ryhma = st.selectbox("Ryhmän valinta tai luonti", list(koneet_data.keys()) + ["Uusi ryhmä"], key="uusi_ryhma")
    kaytettava_ryhma = st.text_input("Uuden ryhmän nimi") if uusi_ryhma == "Uusi ryhmä" else uusi_ryhma
    uusi_nimi = st.text_input("Koneen nimi")
    uusi_id = st.text_input("Koneen ID-numero")
    if st.button("Lisää kone", key="tab3_lisaa_kone"):
        if kaytettava_ryhma and uusi_nimi and uusi_id:
            uusi = pd.DataFrame([{"Kone": uusi_nimi, "ID": uusi_id, "Ryhmä": kaytettava_ryhma}])
            uusi_koneet_df = pd.concat([koneet_df, uusi], ignore_index=True)
            tallenna_koneet(uusi_koneet_df)
            st.success(f"Kone {uusi_nimi} lisätty ryhmään {kaytettava_ryhma}")
            st.experimental_rerun()
        else:
            st.warning("Täytä kaikki kentät.")

    st.subheader("Poista kone")
    if not koneet_df.empty:
        poisto_ryhma = st.selectbox("Valitse ryhmä (poistoa varten)", list(koneet_data.keys()), key="poistoryhma")
        koneet_poisto = koneet_df[koneet_df["Ryhmä"] == poisto_ryhma]
        if not koneet_poisto.empty:
            poisto_nimi = st.selectbox("Valitse kone", koneet_poisto["Kone"].tolist(), key="poistokone")
            if st.button("Poista kone", key="tab3_poista_kone"):
                uusi_koneet_df = koneet_df[~((koneet_df["Ryhmä"] == poisto_ryhma) & (koneet_df["Kone"] == poisto_nimi))]
                tallenna_koneet(uusi_koneet_df)
                st.success(f"Kone {poisto_nimi} poistettu.")
                st.experimental_rerun()
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

