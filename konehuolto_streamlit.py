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

# --------- LOGIN ---------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "login_failed" not in st.session_state:
    st.session_state.login_failed = False

if not st.session_state.logged_in:
    st.title("Kirjaudu sisään")
    username = st.text_input("Käyttäjätunnus", key="login_user")
    password = st.text_input("Salasana", type="password", key="login_pw")
    if st.button("Kirjaudu", key="login_btn"):
        if username == "mattipa" and password == "jdtoro#":
            st.session_state.logged_in = True
            st.session_state.login_failed = False
            st.rerun()
        else:
            st.session_state.login_failed = True
            st.error("Väärä käyttäjätunnus tai salasana.")
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

# --------- MÄÄRITYKSET JA YHTEYDET ---------
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

def lue_koneet():
    ws = get_gsheet_connection("Koneet")
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    for kentta in ["Kone", "ID", "Ryhmä"]:
        if kentta not in df.columns:
            df[kentta] = ""
    return df

def lue_huollot():
    ws = get_gsheet_connection("Huollot")
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    pakolliset = ["HuoltoID", "Kone", "ID", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET
    for kentta in pakolliset:
        if kentta not in df.columns:
            df[kentta] = ""
    return df

def tallenna_koneet(df):
    ws = get_gsheet_connection("Koneet")
    ws.clear()
    if not df.empty:
        ws.update([df.columns.values.tolist()] + df.values.tolist())

def tallenna_huollot(df):
    ws = get_gsheet_connection("Huollot")
    cleaned = df.fillna("").astype(str)
    if not cleaned.empty:
        ws.clear()
        ws.update([cleaned.columns.values.tolist()] + cleaned.values.tolist())
    elif cleaned.empty:
        ws.clear()
        ws.update([["HuoltoID", "Kone", "ID", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"] + LYHENTEET])

def tallenna_kayttotunnit(kone, kone_id, ryhma, ed_tunnit, uusi_tunnit, erotus):
    ws = get_gsheet_connection("Käyttötunnit")
    nyt = datetime.today().strftime("%d.%m.%Y %H:%M")
    uusi_rivi = [[nyt, kone, kone_id, ryhma, ed_tunnit, uusi_tunnit, erotus]]
    # Lisää otsikot jos sheet on tyhjä
    values = ws.get_all_values()
    if not values or not any("Aika" in s for s in values[0]):
        ws.append_row(["Aika", "Kone", "ID", "Ryhmä", "Edellinen huolto", "Uudet tunnit", "Erotus"])
    ws.append_row(uusi_rivi[0])

def ryhmat_ja_koneet(df):
    d = {}
    for _, r in df.iterrows():
        d.setdefault(r["Ryhmä"], []).append({"Kone": r["Kone"], "ID": r["ID"]})
    return d

huolto_df = lue_huollot()
koneet_df = lue_koneet()
koneet_data = ryhmat_ja_koneet(koneet_df) if not koneet_df.empty else {}

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ Lisää huolto", 
    "📋 Huoltohistoria", 
    "🛠 Koneet ja ryhmät",
    "📊 Käyttötunnit"
])

# ----------- TAB 1: LISÄÄ HUOLTO -----------
with tab1:
    st.header("Lisää uusi huoltotapahtuma")
    ryhmat_lista = sorted(list(koneet_data.keys()))
    if not ryhmat_lista:
        st.info("Ei yhtään koneryhmää vielä. Lisää koneita välilehdellä 'Koneet ja ryhmät'.")
    else:
        valittu_ryhma = st.selectbox("Ryhmä", ryhmat_lista, key="tab1_ryhma_select")
        koneet_ryhmaan = koneet_data[valittu_ryhma] if valittu_ryhma else []
        if koneet_ryhmaan:
            koneet_df2 = pd.DataFrame(koneet_ryhmaan)
            kone_valinta = st.radio(
                "Valitse kone:",
                koneet_df2["Kone"].tolist(),
                key="tab1_konevalinta_radio",
                index=0 if len(koneet_df2) > 0 else None
            )
            kone_id = koneet_df2[koneet_df2["Kone"] == kone_valinta]["ID"].values[0]
        else:
            st.info("Valitussa ryhmässä ei ole koneita.")
            kone_id = ""
            kone_valinta = ""

        if kone_id:
            with st.form(key="huolto_form"):
                col1, col2 = st.columns(2)
                with col1:
                    kayttotunnit = st.text_input("Tunnit/km", key="form_tunnit")
                with col2:
                    pvm = st.date_input(
                        "Päivämäärä",
                        value=datetime.today(),
                        min_value=datetime(1990, 1, 1),
                        max_value=datetime(datetime.today().year + 10, 12, 31),
                        key="pvm"
                    )
                st.markdown("#### Huoltokohteet")
                vaihtoehdot = ["--", "Vaihd", "Tark", "OK", "Muu"]
                valinnat = {}
                cols_huolto = st.columns(6)
                for i, pitkä in enumerate(HUOLTOKOHTEET):
                    with cols_huolto[i % 6]:
                        valinnat[HUOLTOKOHTEET[pitkä]] = st.selectbox(
                            f"{pitkä}:", vaihtoehdot,
                            key=f"form_valinta_{pitkä}",
                            index=0
                        )
                vapaa = st.text_input("Vapaa teksti", key="form_vapaa")
                submit = st.form_submit_button("Tallenna huolto")
                if submit:
                    if not valittu_ryhma or not kone_valinta or not kayttotunnit or not kone_id:
                        st.warning("Täytä kaikki kentät!")
                    else:
                        uusi = {
                            "HuoltoID": str(uuid.uuid4())[:8],
                            "Kone": kone_valinta,
                            "ID": kone_id,
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
                            st.rerun()
                        except Exception as e:
                            st.error(f"Tallennus epäonnistui: {e}")

# ----------- TAB 2: HUOLTOHISTORIA + PDF/MUOKKAUS/POISTO -----------
with tab2:
    st.header("Huoltohistoria")
    if huolto_df.empty:
        st.info("Ei huoltoja tallennettu vielä.")
    else:
        # Järjestetään ryhmät ja koneet kuten Koneet-sheetissä
        ryhma_jarjestys = koneet_df["Ryhmä"].drop_duplicates().tolist() if not koneet_df.empty else sorted(huolto_df["Ryhmä"].unique())
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

        # UUSI esikatselufunktio, joka ryhmittelee ryhmän mukaan
        def muodosta_esikatselu_ryhmissa(df, ryhma_jarjestys, koneet_df):
            rows = []
            huolto_cols = ["Tunnit", "Päivämäärä"] + LYHENTEET + ["Vapaa teksti"]
            for ryhma in ryhma_jarjestys:
                koneet_ryhmassa = koneet_df[koneet_df["Ryhmä"] == ryhma]["Kone"].tolist()
                if not koneet_ryhmassa:
                    continue
                rows.append([f"Ryhmä: {ryhma}"] + [""] * (len(huolto_cols) + 1))  # Otsikkorivi ryhmälle
                for kone in koneet_ryhmassa:
                    kone_df = df[(df["Kone"] == kone) & (df["Ryhmä"] == ryhma)].copy()
                    if kone_df.empty:
                        rows.append([kone, ryhma] + [""] * len(huolto_cols))
                        continue
                    kone_df["pvm_dt"] = pd.to_datetime(kone_df["Päivämäärä"], dayfirst=True, errors="coerce")
                    kone_df = kone_df.sort_values("pvm_dt", ascending=True)
                    id_ = kone_df["ID"].iloc[0] if "ID" in kone_df.columns else ""
                    # 1. rivi: koneen nimi, ryhmä, 1. huolto
                    huolto1 = [str(kone_df.iloc[0].get(col, "")) for col in huolto_cols]
                    huolto1 = [fmt_ok(val) for val in huolto1]
                    rows.append([kone, ryhma] + huolto1)
                    # 2. rivi: ID, 2. huolto (tai tyhjät jos vain yksi huolto)
                    if len(kone_df) > 1:
                        huolto2 = [str(kone_df.iloc[1].get(col, "")) for col in huolto_cols]
                        huolto2 = [fmt_ok(val) for val in huolto2]
                        rows.append([id_, ""] + huolto2)
                    else:
                        rows.append([id_, ""] + [""] * len(huolto1))
                    # Mahd. lisää huoltoja
                    for i in range(2, len(kone_df)):
                        huoltoN = [str(kone_df.iloc[i].get(col, "")) for col in huolto_cols]
                        huoltoN = [fmt_ok(val) for val in huoltoN]
                        rows.append(["", ""] + huoltoN)
                    # Tyhjä rivi koneiden väliin
                    rows.append([""] * (2 + len(huolto1)))
            # Poista viimeinen tyhjä rivi
            if rows and all([cell == "" for cell in rows[-1]]):
                rows.pop()
            columns = ["Kone", "Ryhmä", "Tunnit", "Päivämäärä"] + LYHENTEET + ["Vapaa teksti"]
            return pd.DataFrame(rows, columns=columns)

        # Esikatselu DataFrame
        df_naytto = muodosta_esikatselu_ryhmissa(filt, ryhma_jarjestys, koneet_df)
        st.dataframe(df_naytto, hide_index=True, use_container_width=True)

        # MUOKKAUS ja POISTO
        id_valinnat = [
            f"{row['Kone']} ({row['ID']}) {row['Päivämäärä']} (HuoltoID: {row['HuoltoID']})"
            for _, row in df.iterrows()
        ]
        valittu_id_valinta = st.selectbox("Valitse muokattava huolto", [""] + id_valinnat, key="tab2_muokkaa_id")

        if valittu_id_valinta:
            valittu_huoltoid = valittu_id_valinta.split("HuoltoID: ")[-1].replace(")", "").strip()
            valittu = df[df["HuoltoID"].astype(str) == valittu_huoltoid].iloc[0]
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
                idx = df[df["HuoltoID"].astype(str) == valittu_huoltoid].index[0]
                df.at[idx, "Tunnit"] = uusi_tunnit
                df.at[idx, "Päivämäärä"] = uusi_pvm
                df.at[idx, "Vapaa teksti"] = uusi_vapaa
                for lyhenne in uusi_kohta:
                    df.at[idx, lyhenne] = uusi_kohta[lyhenne]
                tallenna_huollot(df)
                st.success("Tallennettu!")
                st.rerun()
            if st.button("Poista tämä huolto", key="tab2_poista_huolto"):
                df = df[df["HuoltoID"].astype(str) != valittu_huoltoid]
                tallenna_huollot(df)
                st.success("Huolto poistettu!")
                st.rerun()

        # --- PDF-lataus, järjestys ryhmän mukaan ---
        def tee_pdf_data_ryhmissa(df, ryhma_jarjestys, koneet_df):
            rows = []
            huolto_cols = ["Tunnit", "Päivämäärä"] + LYHENTEET + ["Vapaa teksti"]
            for ryhma in ryhma_jarjestys:
                koneet_ryhmassa = koneet_df[koneet_df["Ryhmä"] == ryhma]["Kone"].tolist()
                if not koneet_ryhmassa:
                    continue
                rows.append([f"Ryhmä: {ryhma}"] + [""] * (len(huolto_cols) + 1))
                for kone in koneet_ryhmassa:
                    kone_df = df[(df["Kone"] == kone) & (df["Ryhmä"] == ryhma)].copy()
                    if kone_df.empty:
                        rows.append([kone, ryhma] + [""] * len(huolto_cols))
                        continue
                    kone_df["pvm_dt"] = pd.to_datetime(kone_df["Päivämäärä"], dayfirst=True, errors="coerce")
                    kone_df = kone_df.sort_values("pvm_dt", ascending=True)
                    id_ = kone_df["ID"].iloc[0] if "ID" in kone_df.columns else ""
                    huolto1 = [str(kone_df.iloc[0].get(col, "")) for col in huolto_cols]
                    huolto1 = [fmt_ok(val) for val in huolto1]
                    rows.append([kone, ryhma] + huolto1)
                    if len(kone_df) > 1:
                        huolto2 = [str(kone_df.iloc[1].get(col, "")) for col in huolto_cols]
                        huolto2 = [fmt_ok(val) for val in huolto2]
                        rows.append([id_, ""] + huolto2)
                    else:
                        rows.append([id_, ""] + [""] * len(huolto1))
                    for i in range(2, len(kone_df)):
                        huoltoN = [str(kone_df.iloc[i].get(col, "")) for col in huolto_cols]
                        huoltoN = [fmt_ok(val) for val in huoltoN]
                        rows.append(["", ""] + huoltoN)
                    rows.append([""] * (2 + len(huolto1)))
            if rows and all([cell == "" for cell in rows[-1]]):
                rows.pop()
            columns = ["Kone", "Ryhmä", "Tunnit", "Päivämäärä"] + LYHENTEET + ["Vapaa teksti"]
            return [columns] + rows

        def lataa_pdf(df, ryhma_jarjestys, koneet_df):
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
            data = tee_pdf_data_ryhmissa(df, ryhma_jarjestys, koneet_df)

            def pdf_rivi(rivi):
                if str(rivi[0]).startswith("Ryhmä:"):
                    # Ryhmän otsikkorivi pdf:ssä bold & taustaväri
                    style = ParagraphStyle(name="ryhma", fontName="Helvetica-Bold", fontSize=10, textColor=colors.white, backColor=colors.darkblue)
                    return [Paragraph(str(rivi[0]), style)] + [""] * (len(rivi) - 1)
                uusi = []
                for cell in rivi:
                    if str(cell).strip().upper() in ["✔", "OK"]:
                        uusi.append(Paragraph('<font color="green">✔</font>', vihrea))
                    else:
                        uusi.append(str(cell) if cell is not None else "")
                return uusi

            table_data = [data[0]] + [pdf_rivi(r) for r in data[1:]]
            sarakeleveys = [110, 80, 55, 60] + [30 for _ in LYHENTEET] + [160]
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
                # Ryhmän otsikkorivit tumma tausta (esim. sininen)
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke)
            ]
            # Korostetaan ryhmärivit pdf:ssä
            for idx, row in enumerate(table_data[1:], start=1):
                if hasattr(row[0], "getPlainText") and "Ryhmä:" in row[0].getPlainText():
                    table_styles.append(('BACKGROUND', (0, idx), (-1, idx), colors.darkblue))
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
            pdfdata = lataa_pdf(filt, ryhma_jarjestys, koneet_df)
            st.download_button(
                label="Lataa PDF-tiedosto",
                data=pdfdata,
                file_name="huoltohistoria.pdf",
                mime="application/pdf"
            )



# ----------- TAB 3: KONEET JA RYHMÄT -----------
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
            st.rerun()
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

# ----------- TAB 4: KÄYTTÖTUNNIT -----------
with tab4:
    st.header("Kaikkien koneiden käyttötunnit ja erotus")
    if koneet_df.empty:
        st.info("Ei koneita lisättynä.")
    else:
        koneet_nimet = koneet_df["Kone"].tolist()
        lista = []
        for i, kone in enumerate(koneet_nimet):
            ryhma = koneet_df[koneet_df["Kone"] == kone]["Ryhmä"].values[0] if "Ryhmä" in koneet_df.columns else ""
            kone_id = koneet_df[koneet_df["Kone"] == kone]["ID"].values[0] if "ID" in koneet_df.columns else ""
            huollot_koneelle = huolto_df[huolto_df["Kone"] == kone].copy()
            huollot_koneelle["Pvm_dt"] = pd.to_datetime(huollot_koneelle["Päivämäärä"], dayfirst=True, errors="coerce")
            huollot_koneelle = huollot_koneelle.sort_values("Pvm_dt", ascending=False)
            if not huollot_koneelle.empty:
                viimeisin_huolto = huollot_koneelle.iloc[0]
                viimeiset_tunnit = float(str(viimeisin_huolto.get("Tunnit", 0)).replace(",", ".") or 0)
                viimeisin_pvm = viimeisin_huolto.get("Päivämäärä", "")
            else:
                viimeiset_tunnit = 0
                viimeisin_pvm = "-"
            lista.append({
                "Kone": kone,
                "Ryhmä": ryhma,
                "ID": kone_id,
                "Viimeisin huolto (pvm)": viimeisin_pvm,
                "Viimeisin huolto (tunnit)": viimeiset_tunnit,
            })

        df_tunnit = pd.DataFrame(lista)
        df_tunnit["Syötä uudet tunnit"] = [
            st.number_input(
                f"Uudet tunnit ({row['Kone']} / {row['Ryhmä']})",
                min_value=0.0,
                value=row["Viimeisin huolto (tunnit)"],
                step=1.0,
                key=f"tab4_tunnit_{i}"
            ) for i, row in df_tunnit.iterrows()
        ]
        df_tunnit["Erotus"] = df_tunnit["Syötä uudet tunnit"] - df_tunnit["Viimeisin huolto (tunnit)"]

        st.dataframe(
            df_tunnit[["Kone", "Ryhmä", "Viimeisin huolto (pvm)", "Viimeisin huolto (tunnit)", "Syötä uudet tunnit", "Erotus"]],
            hide_index=True
        )

        # --- PDF-lataus, sama tyyli kuin tab2:ssa (reportlab) ---
        from io import BytesIO
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch, mm
        from datetime import datetime

        def create_tab4_pdf(df):
            buffer = BytesIO()
            otsikkotyyli = ParagraphStyle(name="otsikko", fontName="Helvetica-Bold", fontSize=16)
            paivays = Paragraph(datetime.today().strftime("%d.%m.%Y"), ParagraphStyle("date", fontSize=12, alignment=2))
            otsikko = Paragraph("Kaikkien koneiden käyttötunnit ja erotus", otsikkotyyli)

            # Taulukkodata
            columns = ["Kone", "Ryhmä", "Viimeisin huolto (pvm)", "Viimeisin huolto (tunnit)", "Syötä uudet tunnit", "Erotus"]
            data = [columns] + [[
                str(row["Kone"]),
                str(row["Ryhmä"]),
                str(row["Viimeisin huolto (pvm)"]),
                str(row["Viimeisin huolto (tunnit)"]),
                str(row["Syötä uudet tunnit"]),
                str(row["Erotus"])
            ] for _, row in df.iterrows()]

            sarakeleveys = [150, 120, 130, 130, 100, 55]
            table = Table(data, repeatRows=1, colWidths=sarakeleveys)
            table_styles = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.teal),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]
            table.setStyle(TableStyle(table_styles))

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

        pdf_buffer = create_tab4_pdf(df_tunnit)

        st.download_button(
            label="Lataa PDF-tiedosto",
            data=pdf_buffer,
            file_name="kaikkien_koneiden_tunnit.pdf",
            mime="application/pdf"
        )
        # --- /PDF-lataus ---

        if st.button("Tallenna kaikkien koneiden tunnit", key="tab4_tallenna_kaikki"):
            try:
                ws = get_gsheet_connection("Käyttötunnit")
                nyt = datetime.today().strftime("%d.%m.%Y %H:%M")
                values = ws.get_all_values()
                if not values or not any("Aika" in s for s in values[0]):
                    ws.append_row(["Aika", "Kone", "Ryhmä", "Edellinen huolto", "Uudet tunnit", "Erotus"])
                for idx, row in df_tunnit.iterrows():
                    ws.append_row([
                        nyt,
                        row["Kone"],
                        row["Ryhmä"],
                        row["Viimeisin huolto (tunnit)"],
                        row["Syötä uudet tunnit"],
                        row["Erotus"]
                    ])
                st.success("Kaikkien koneiden tunnit tallennettu Google Sheetiin!")
            except Exception as e:
                st.error(f"Tallennus epäonnistui: {e}")




























