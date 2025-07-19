import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import base64
import uuid

# --- LOGIN ---
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

# --- TAUSTAKUVA (banneri) ---
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
        padding: 100px 0 100px 0;
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

# --- HUOLTOKOHTEET ---
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

# --- GOOGLE SHEETS API ---
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

# --- Lisää huolto ---
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
            st.write("DEBUG – koneet_df2:", koneet_df2)
            st.write("DEBUG – sarakkeet:", koneet_df2.columns.tolist())

            # Haetaan tarkasti oikeat sarakkeet
            if "Kone" in koneet_df2.columns and "ID" in koneet_df2.columns:
                kone_sarake = "Kone"
                id_sarake = "ID"
            else:
                st.error(f"SHEETISSÄ EI OLE SARAKEOTSIKOITA 'Kone' ja 'ID'.")
                st.stop()

            koneet_df2[kone_sarake] = koneet_df2[kone_sarake].fillna("Tuntematon kone")
            koneet_df2["valinta"] = koneet_df2[kone_sarake]
            kone_valinta = st.radio(
                "Valitse kone:",
                koneet_df2["valinta"].tolist(),
                key="konevalinta_radio",
                index=0 if len(koneet_df2) > 0 else None
            )
            valittu_kone_nimi = kone_valinta
            try:
                kone_id = koneet_df2[koneet_df2[kone_sarake] == valittu_kone_nimi][id_sarake].values[0]
            except Exception as e:
                st.error(f"Virhe koneen ID:n haussa: {e}")
                kone_id = ""
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
                        "ID-numero": kone_id,  # Ei Sheetissä, mutta voidaan hyödyntää!
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
                    st.rerun()
)



# --- Huoltohistoria + Muokkaus + PDF ---
with tab2:
    st.header("Huoltohistoria")
    if huolto_df.empty or huolto_df["Kone"].dropna().empty:
        st.info("Ei huoltoja tallennettu vielä.")
    else:
        df = huolto_df.copy()
        df = df.reset_index(drop=True)

        # Suodattimet
        kaikki_ryhmat = ["Kaikki"] + sorted([r for r in df["Ryhmä"].dropna().unique() if r])
        valittu_ryhma = st.selectbox("Suodata ryhmän mukaan", kaikki_ryhmat, index=0, key="ryhma_suodatin_tab2")
        df_ryhma = df if valittu_ryhma == "Kaikki" else df[df["Ryhmä"] == valittu_ryhma]

        kaikki_koneet = ["Kaikki"] + sorted([k for k in df_ryhma["Kone"].dropna().unique() if k])
        valittu_kone = st.selectbox("Suodata koneen mukaan", kaikki_koneet, index=0, key="kone_suodatin_tab2")
        df_kone = df_ryhma if valittu_kone == "Kaikki" else df_ryhma[df_ryhma["Kone"] == valittu_kone]

        df = df_kone.reset_index(drop=True)

        def fmt_ok(x):
            return "✔" if str(x).strip().upper() == "OK" else x

        def esikatselu_df(df):
            rows = []
            for kone in df["Kone"].unique():
                kone_df = df[df["Kone"] == kone]
                eka = True
                for idx, row in kone_df.iterrows():
                    if eka:
                        rivi = [
                            kone,
                            row.get("Ryhmä", ""),
                            row.get("Tunnit", ""),
                            row.get("Päivämäärä", ""),
                            row.get("Vapaa teksti", ""),
                        ] + [fmt_ok(row.get(k, "")) for k in LYHENTEET]
                        rows.append(rivi)
                        id_rivi = [
                            row.get("ID", ""), "", "", "", ""
                        ] + ["" for k in LYHENTEET]
                        rows.append(id_rivi)
                        eka = False
                    else:
                        rivi = [
                            "",
                            row.get("Ryhmä", ""),
                            row.get("Tunnit", ""),
                            row.get("Päivämäärä", ""),
                            row.get("Vapaa teksti", ""),
                        ] + [fmt_ok(row.get(k, "")) for k in LYHENTEET]
                        rows.append(rivi)
            columns = ["Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
            return pd.DataFrame(rows, columns=columns)

        df_naytto = esikatselu_df(df)
        st.dataframe(df_naytto, hide_index=True, key="df_naytto_tab2")

        muokattava_id = st.selectbox("Valitse muokattava huolto", [""] + df["ID"].astype(str).tolist(), key="muokattava_id_tab2")
        if muokattava_id:
            valittu = df[df["ID"].astype(str) == muokattava_id].iloc[0]
            uusi_tunnit = st.text_input("Tunnit/km", value=valittu.get("Tunnit", ""), key="uusi_tunnit_tab2")
            uusi_pvm = st.text_input("Päivämäärä", value=valittu.get("Päivämäärä", ""), key="uusi_pvm_tab2")
            uusi_vapaa = st.text_input("Vapaa teksti", value=valittu.get("Vapaa teksti", ""), key="uusi_vapaa_tab2")
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
                    key=f"edit_{lyhenne}_tab2"
                )
            if st.button("Tallenna muutokset", key="tallenna_tab2"):
                idx = df[df["ID"].astype(str) == muokattava_id].index[0]
                df.at[idx, "Tunnit"] = uusi_tunnit
                df.at[idx, "Päivämäärä"] = uusi_pvm
                df.at[idx, "Vapaa teksti"] = uusi_vapaa
                for lyhenne in uusi_kohta:
                    df.at[idx, lyhenne] = uusi_kohta[lyhenne]
                tallenna_huollot(df)
                st.success("Tallennettu!")
                st.rerun()
            if st.button("Poista tämä huolto", key="poista_tab2"):
                df = df[df["ID"].astype(str) != muokattava_id]
                tallenna_huollot(df)
                st.success("Huolto poistettu!")
                st.rerun()

        # --- PDF-lataus ---
        def lataa_pdf(df):
            buffer = BytesIO()
            vihrea = ParagraphStyle(name="vihrea", textColor=colors.green, fontName="Helvetica-Bold", fontSize=8)
            otsikkotyyli = ParagraphStyle(
                name="OtsikkoIso",
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=22,
                alignment=0
            )
            doc = SimpleDocTemplate(
                buffer, pagesize=landscape(A4),
                rightMargin=0.5 * inch, leftMargin=0.5 * inch,
                topMargin=0.7 * inch, bottomMargin=0.5 * inch
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
            def pdf_rivi(rivi):
                uusi = []
                for cell in rivi:
                    if str(cell).strip().upper() in ["✔", "OK"]:
                        uusi.append(Paragraph('<font color="green">✔</font>', vihrea))
                    else:
                        uusi.append(str(cell) if cell is not None else "")
                return uusi
            table_data = [list(df.columns)] + [pdf_rivi(list(row)) for _, row in df.iterrows()]
            sarakeleveys = [110, 80, 60, 80, 140] + [32 for _ in range(len(df.columns)-5)]
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
            def pdf_footer(canvas, doc):
                canvas.saveState()
                canvas.setFont('Helvetica', 8)
                canvas.drawCentredString(420, 20, f"Sivu {doc.page}")
                canvas.restoreState()
            elements = [
                Spacer(1, 4 * inch / 10),
                otsikko_paivays_table,
                Spacer(1, 0.2 * inch),
                table
            ]
            doc.build(elements, onFirstPage=pdf_footer, onLaterPages=pdf_footer)
            buffer.seek(0)
            return buffer

        if st.button("Lataa PDF", key="pdf_tab2"):
            pdfdata = lataa_pdf(df_naytto)
            st.download_button(
                label="Lataa PDF-tiedosto",
                data=pdfdata,
                file_name="huoltohistoria.pdf",
                mime="application/pdf",
                key="pdf_dl_tab2"
            )

# --- Koneiden ja ryhmien hallinta (tab3) pysyy entisellään ---



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
