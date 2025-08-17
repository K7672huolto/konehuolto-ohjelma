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
            # clear_on_submit tyhjentää kentät automaattisesti tallennuksen jälkeen
            with st.form(key="huolto_form", clear_on_submit=True):
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
                            st.rerun()  # Lataa sivun uudelleen, lomake tyhjenee clear_on_submit:n ansiosta
                        except Exception as e:
                            st.error(f"Tallennus epäonnistui: {e}")



# ----------- TAB 2: HUOLTOHISTORIA + PDF/MUOKKAUS/POISTO -----------
with tab2:
    st.header("Huoltohistoria")
    if huolto_df.empty:
        st.info("Ei huoltoja tallennettu vielä.")
    else:
        # --- Pohjadatat ---
        alkuperainen_ryhma_jarjestys = (
            koneet_df["Ryhmä"].drop_duplicates().tolist()
            if not koneet_df.empty
            else sorted(huolto_df["Ryhmä"].unique())
        )
        alkuperainen_koneet_df = koneet_df.copy()
        df = huolto_df.copy().reset_index(drop=True)

        # --- Suodatus UI ---
        ryhmat = ["Kaikki"] + sorted(df["Ryhmä"].unique())
        valittu_ryhma = st.selectbox("Suodata ryhmän mukaan", ryhmat, key="tab2_ryhma")

        filt = df if valittu_ryhma == "Kaikki" else df[df["Ryhmä"] == valittu_ryhma]
        koneet = ["Kaikki"] + sorted(filt["Kone"].unique())
        valittu_kone = st.selectbox("Suodata koneen mukaan", koneet, key="tab2_kone")

        filt = filt if valittu_kone == "Kaikki" else filt[filt["Kone"] == valittu_kone]

        # --- Järjestys esikatseluun (koneet koneet_df:n mukaisessa järjestyksessä) ---
        if valittu_ryhma != "Kaikki":
            ryhma_jarjestys = [valittu_ryhma]
            koneet_df_esikatselu = alkuperainen_koneet_df[alkuperainen_koneet_df["Ryhmä"] == valittu_ryhma].copy()
        else:
            ryhma_jarjestys = alkuperainen_ryhma_jarjestys
            koneet_df_esikatselu = alkuperainen_koneet_df.copy()

        if valittu_kone != "Kaikki":
            koneet_df_esikatselu = koneet_df_esikatselu[koneet_df_esikatselu["Kone"] == valittu_kone].copy()

        # ✔ -logiikka
        def fmt_ok(x):
            return "✔" if str(x).strip().upper() == "OK" else x

        # --- Esikatselu: ei ryhmäotsikkorivejä, kronologinen per kone ---
        def muodosta_esikatselu_ryhmissa(df_src, ryhmajarj, koneet_src_df):
            rows = []
            huolto_cols = ["Tunnit", "Päivämäärä"] + LYHENTEET + ["Vapaa teksti"]

            for ryhma in ryhmajarj:
                koneet_ryhmassa = koneet_src_df[koneet_src_df["Ryhmä"] == ryhma]["Kone"].tolist()
                if not koneet_ryhmassa:
                    continue

                for kone in koneet_ryhmassa:
                    kone_df = df_src[(df_src["Kone"] == kone) & (df_src["Ryhmä"] == ryhma)].copy()
                    if kone_df.empty:
                        rows.append([kone, ryhma] + [""] * len(huolto_cols))
                        continue

                    # Kronologinen järjestys koneen sisällä
                    kone_df["pvm_dt"] = pd.to_datetime(kone_df["Päivämäärä"], dayfirst=True, errors="coerce")
                    kone_df = kone_df.sort_values("pvm_dt", ascending=True)

                    id_ = kone_df["ID"].iloc[0] if "ID" in kone_df.columns else ""

                    # 1. huoltorivi: Kone + Ryhmä
                    huolto1 = [str(kone_df.iloc[0].get(col, "")) for col in huolto_cols]
                    huolto1 = [fmt_ok(val) for val in huolto1]
                    rows.append([kone, ryhma] + huolto1)

                    # 2. rivi: ID + (Ryhmä tyhjä)
                    if len(kone_df) > 1:
                        huolto2 = [str(kone_df.iloc[1].get(col, "")) for col in huolto_cols]
                        huolto2 = [fmt_ok(val) for val in huolto2]
                        rows.append([id_, ""] + huolto2)
                    else:
                        rows.append([id_, ""] + [""] * len(huolto1))

                    # Mahdolliset lisähuollot
                    for i in range(2, len(kone_df)):
                        huoltoN = [str(kone_df.iloc[i].get(col, "")) for col in huolto_cols]
                        huoltoN = [fmt_ok(val) for val in huoltoN]
                        rows.append(["", ""] + huoltoN)

                    # Tyhjä erotusrivi koneiden väliin
                    rows.append([""] * (2 + len(huolto1)))

            if rows and all(cell == "" for cell in rows[-1]):
                rows.pop()

            columns = ["Kone", "Ryhmä", "Tunnit", "Päivämäärä"] + LYHENTEET + ["Vapaa teksti"]
            return pd.DataFrame(rows, columns=columns)

        # --- Esikatselu DataFrame ---
        df_naytto = muodosta_esikatselu_ryhmissa(filt, ryhma_jarjestys, koneet_df_esikatselu)
        st.dataframe(
            df_naytto,
            hide_index=True,
            use_container_width=True,
            # column_config={"Ryhmä": st.column_config.Column(width="medium")}
        )

        # --- MUOKKAUS JA POISTO ---
        id_valinnat = [
            f"{row['Kone']} ({row['ID']}) {row['Päivämäärä']} (HuoltoID: {row['HuoltoID']})"
            for _, row in filt.iterrows()
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

            col_save, col_del = st.columns(2)

            if col_save.button("Tallenna muutokset", key="tab2_tallenna_muokkaa"):
                # Päivitä Huollot
                idx = df[df["HuoltoID"].astype(str) == valittu_huoltoid].index[0]
                df.at[idx, "Tunnit"] = uusi_tunnit
                df.at[idx, "Päivämäärä"] = uusi_pvm
                df.at[idx, "Vapaa teksti"] = uusi_vapaa
                for lyhenne in uusi_kohta:
                    df.at[idx, lyhenne] = uusi_kohta[lyhenne]
                tallenna_huollot(df)

                # --- Päivitä / lisää myös Käyttötunnit-sheet ---
                try:
                    ws_tunnit = get_gsheet_connection("Käyttötunnit")
                    values = ws_tunnit.get_all_values()
                    # Headerit jos tyhjä
                    if not values or not any("Aika" in s for s in values[0]):
                        ws_tunnit.append_row(["Aika", "Kone", "Ryhmä", "Uudet tunnit", "Erotus"])

                    data = ws_tunnit.get_all_records()
                    kone_nimi = str(valittu.get("Kone", ""))
                    ryhma_nimi = str(valittu.get("Ryhmä", ""))
                    try:
                        uusi_arvo = int(float(str(uusi_tunnit).replace(",", ".")))
                    except:
                        uusi_arvo = 0
                    aika_nyt = datetime.today().strftime("%d.%m.%Y %H:%M")

                    paivitetty = False
                    # etsi rivinumero päivitystä varten (alkaa 2:sta otsikon jälkeen)
                    for i, r in enumerate(data, start=2):
                        if r.get("Kone") == kone_nimi:
                            ws_tunnit.update(f"A{i}:E{i}", [[aika_nyt, kone_nimi, ryhma_nimi, uusi_arvo, ""]])
                            paivitetty = True
                            break
                    if not paivitetty:
                        ws_tunnit.append_row([aika_nyt, kone_nimi, ryhma_nimi, uusi_arvo, ""])
                except Exception as e:
                    st.error(f"Käyttötunnit-sheetin päivitys epäonnistui: {e}")

                st.success("Tallennettu (Huollot + Käyttötunnit)!")
                st.rerun()

            if col_del.button("Poista tämä huolto", key="tab2_poista_huolto"):
                df = df[df["HuoltoID"].astype(str) != valittu_huoltoid]
                tallenna_huollot(df)
                st.success("Huolto poistettu!")
                st.rerun()

        # --- PDF: sama rakenne kuin esikatselussa, ei ryhmäotsikoita, koneen nimi bold ---
        from io import BytesIO
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import inch, mm

        def lataa_pdf_ilman_ryhmaotsikoita(df_src, ryhmajarj, koneet_src_df):
            buffer = BytesIO()
            vihrea = ParagraphStyle(name="vihrea", textColor=colors.green, fontName="Helvetica-Bold", fontSize=8)
            otsikkotyyli = ParagraphStyle(name="otsikko", fontName="Helvetica-Bold", fontSize=16)
            styles = getSampleStyleSheet()
            kone_bold = ParagraphStyle(name="kone_bold", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8)
            norm = ParagraphStyle(name="norm", parent=styles["Normal"], fontSize=8)

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

            # Rakenna data kuten esikatselussa
            rows = []
            huolto_cols = ["Tunnit", "Päivämäärä"] + LYHENTEET + ["Vapaa teksti"]

            for ryhma in ryhmajarj:
                koneet_ryhmassa = koneet_src_df[koneet_src_df["Ryhmä"] == ryhma]["Kone"].tolist()
                if not koneet_ryhmassa:
                    continue

                for kone in koneet_ryhmassa:
                    kone_df = df_src[(df_src["Kone"] == kone) & (df_src["Ryhmä"] == ryhma)].copy()
                    if kone_df.empty:
                        rows.append([kone, ryhma] + [""] * len(huolto_cols))
                        continue

                    kone_df["pvm_dt"] = pd.to_datetime(kone_df["Päivämäärä"], dayfirst=True, errors="coerce")
                    kone_df = kone_df.sort_values("pvm_dt", ascending=True)

                    id_ = kone_df["ID"].iloc[0] if "ID" in kone_df.columns else ""

                    huolto1 = [str(kone_df.iloc[0].get(c, "")) for c in huolto_cols]
                    huolto1 = ["✔" if str(v).strip().upper() == "OK" else v for v in huolto1]
                    rows.append([kone, ryhma] + huolto1)

                    if len(kone_df) > 1:
                        huolto2 = [str(kone_df.iloc[1].get(c, "")) for c in huolto_cols]
                        huolto2 = ["✔" if str(v).strip().upper() == "OK" else v for v in huolto2]
                        rows.append([id_, ""] + huolto2)
                    else:
                        rows.append([id_, ""] + [""] * len(huolto1))

                    for i in range(2, len(kone_df)):
                        huoltoN = [str(kone_df.iloc[i].get(c, "")) for c in huolto_cols]
                        huoltoN = ["✔" if str(v).strip().upper() == "OK" else v for v in huoltoN]
                        rows.append(["", ""] + huoltoN)

                    rows.append([""] * (2 + len(huolto1)))

            if rows and all(cell == "" for cell in rows[-1]):
                rows.pop()

            columns = ["Kone", "Ryhmä", "Tunnit", "Päivämäärä"] + LYHENTEET + ["Vapaa teksti"]
            data = [columns]

            # Muunna PDF-solut; koneen nimi bold, ✔ vihreänä
            def pdf_rivi(rivi):
                out = []
                for col_idx, cell in enumerate(rivi):
                    teksti = "" if cell is None else str(cell)
                    if col_idx == 0 and teksti.strip() != "":
                        out.append(Paragraph(teksti, kone_bold))
                    elif teksti.strip() == "✔":
                        out.append(Paragraph('<font color="green">✔</font>', vihrea))
                    else:
                        out.append(Paragraph(teksti, norm))
                return out

            data += [pdf_rivi(r) for r in rows]

            sarakeleveys = [110, 80, 55, 60] + [30 for _ in LYHENTEET] + [160]
            table = Table(data, repeatRows=1, colWidths=sarakeleveys)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.teal),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))

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

        # Näppäin + lataus
        if st.button("Lataa PDF", key="lataa_pdf_tab2"):
            pdfdata = lataa_pdf_ilman_ryhmaotsikoita(filt, ryhma_jarjestys, koneet_df_esikatselu)
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
# ----------- TAB 4: KÄYTTÖTUNNIT -----------
with tab4:
    st.header("Kaikkien koneiden käyttötunnit ja erotus")

    from io import BytesIO
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch, mm

    def lue_kayttotunnit_sheet():
        try:
            ws = get_gsheet_connection("Käyttötunnit")
            values = ws.get_all_values()
            if not values:
                cols = ["Aika", "Kone", "Ryhmä", "Edellinen huolto", "Uudet tunnit", "Erotus"]
                return pd.DataFrame(columns=cols)
            df = pd.DataFrame(values[1:], columns=values[0]) if len(values) > 1 else pd.DataFrame(columns=values[0])
            for c in ["Aika", "Kone", "Ryhmä", "Edellinen huolto", "Uudet tunnit", "Erotus"]:
                if c not in df.columns:
                    df[c] = ""
            return df
        except:
            return pd.DataFrame(columns=["Aika", "Kone", "Ryhmä", "Edellinen huolto", "Uudet tunnit", "Erotus"])

    def viimeisin_huolto_koneelle(kone, ryhma):
        df_k = huolto_df[(huolto_df["Kone"] == kone) & (huolto_df["Ryhmä"] == ryhma)].copy()
        if df_k.empty:
            return 0, "-"
        df_k["pvm_dt"] = pd.to_datetime(df_k["Päivämäärä"], dayfirst=True, errors="coerce")
        df_k = df_k.sort_values("pvm_dt", ascending=False)
        pvm = str(df_k.iloc[0]["Päivämäärä"])
        try:
            tunnit = int(float(str(df_k.iloc[0].get("Tunnit", "0")).replace(",", ".")))
        except:
            tunnit = 0
        return tunnit, pvm

    def viimeisin_tallennettu_kayttotunti(df_kt, kone, ryhma):
        if df_kt.empty:
            return None
        d = df_kt[(df_kt["Kone"] == kone) & (df_kt["Ryhmä"] == ryhma)].copy()
        if d.empty:
            return None
        def parse_aika(x):
            try:
                return datetime.strptime(str(x), "%d.%m.%Y %H:%M")
            except:
                return datetime.min
        d["Aika_dt"] = d["Aika"].apply(parse_aika)
        d = d.sort_values("Aika_dt", ascending=False)
        try:
            return int(float(str(d.iloc[0]["Uudet tunnit"]).replace(",", ".")))
        except:
            return None

    if koneet_df.empty:
        st.info("Ei koneita lisättynä.")
    else:
        kt_df = lue_kayttotunnit_sheet()
        rivit = []
        for i, (_, r) in enumerate(koneet_df.iterrows()):
            kone = str(r.get("Kone", ""))
            ryhma = str(r.get("Ryhmä", ""))
            huolto_tunnit, huolto_pvm = viimeisin_huolto_koneelle(kone, ryhma)
            tallennettu = viimeisin_tallennettu_kayttotunti(kt_df, kone, ryhma)
            oletus_uudet = tallennettu if tallennettu is not None else huolto_tunnit
            uudet_tunnit = st.number_input(
                f"Uudet tunnit: {kone} / {ryhma}",
                min_value=0,
                value=int(oletus_uudet),
                step=1,
                key=f"tab4_tunnit_{i}"
            )
            erotus = int(uudet_tunnit) - int(huolto_tunnit)
            rivit.append({
                "Kone": kone,
                "Ryhmä": ryhma,
                "Viimeisin huolto (pvm)": huolto_pvm,
                "Viimeisin huolto (tunnit)": int(huolto_tunnit),
                "Syötä uudet tunnit": int(uudet_tunnit),
                "Erotus": int(erotus),
            })
        df_tunnit = pd.DataFrame(rivit)

        def style_df(df):
            styled = df.style.format({
                "Viimeisin huolto (tunnit)": "{:.0f}",
                "Syötä uudet tunnit": "{:.0f}",
                "Erotus": "{:.0f}",
            })
            styled = styled.set_properties(subset=["Kone"], **{"font-weight": "bold"})
            styled = styled.set_properties(subset=["Erotus"], **{"color": "red"})
            return styled

        st.write(style_df(df_tunnit))

        # --- PDF ---
        def create_tab4_pdf(df):
            buffer = BytesIO()
            otsikkotyyli = ParagraphStyle(name="otsikko", fontName="Helvetica-Bold", fontSize=16)
            paivays = Paragraph(datetime.today().strftime("%d.%m.%Y"), ParagraphStyle("date", fontSize=12, alignment=2))
            otsikko = Paragraph("Kaikkien koneiden käyttötunnit ja erotus", otsikkotyyli)

            columns = ["Kone", "Ryhmä", "Viimeisin huolto (pvm)", "Viimeisin huolto (tunnit)", "Syötä uudet tunnit", "Erotus"]
            data = [columns]
            for _, row in df.iterrows():
                data.append([
                    Paragraph(f"<b>{row['Kone']}</b>", ParagraphStyle("default")),
                    str(row["Ryhmä"]),
                    str(row["Viimeisin huolto (pvm)"]),
                    str(row["Viimeisin huolto (tunnit)"]),
                    str(row["Syötä uudet tunnit"]),
                    Paragraph(f"<font color='red'>{row['Erotus']}</font>", ParagraphStyle("default"))
                ])

            table = Table(data, repeatRows=1, colWidths=[180, 100, 130, 120, 110, 70])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.teal),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))

            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                                    rightMargin=0.5*inch, leftMargin=0.5*inch,
                                    topMargin=0.7*inch, bottomMargin=0.5*inch)
            doc.build([Spacer(1,4*mm), 
                       Table([[otsikko, paivays]], colWidths=[340, 340], style=[
                           ("ALIGN",(0,0),(0,0),"LEFT"),
                           ("ALIGN",(1,0),(1,0),"RIGHT")
                       ]),
                       Spacer(1,4*mm), table])
            buffer.seek(0)
            return buffer

        pdf_buffer = create_tab4_pdf(df_tunnit)
        st.download_button("Lataa PDF", data=pdf_buffer, file_name="kayttotunnit.pdf", mime="application/pdf")

        # --- TALLENNUS ---
        if st.button("Tallenna kaikkien koneiden tunnit", key="tab4_tallenna_kaikki"):
            try:
                ws = get_gsheet_connection("Käyttötunnit")
                values = ws.get_all_values()
                cols = ["Aika", "Kone", "Ryhmä", "Edellinen huolto", "Uudet tunnit", "Erotus"]
                if not values:
                    current = pd.DataFrame(columns=cols)
                else:
                    current = pd.DataFrame(values[1:], columns=values[0]) if len(values)>1 else pd.DataFrame(columns=values[0])
                    for c in cols:
                        if c not in current.columns:
                            current[c] = ""
                if not current.empty:
                    current["_key"] = current["Kone"]+"||"+current["Ryhmä"]
                else:
                    current["_key"] = []
                nyt = datetime.today().strftime("%d.%m.%Y %H:%M")
                new_rows = []
                for _, row in df_tunnit.iterrows():
                    key = f"{row['Kone']}||{row['Ryhmä']}"
                    uusi = {"Aika": nyt, "Kone": row["Kone"], "Ryhmä": row["Ryhmä"],
                            "Edellinen huolto": str(row["Viimeisin huolto (tunnit)"]),
                            "Uudet tunnit": str(row["Syötä uudet tunnit"]),
                            "Erotus": str(row["Erotus"]), "_key": key}
                    mask = (current["_key"]==key)
                    if not current.empty and mask.any():
                        idx = current[mask].index[0]
                        for c in ["Aika","Edellinen huolto","Uudet tunnit","Erotus"]:
                            current.at[idx,c] = uusi[c]
                    else:
                        new_rows.append(uusi)
                if new_rows:
                    current = pd.concat([current,pd.DataFrame(new_rows)],ignore_index=True)
                if "_key" in current.columns:
                    current = current.drop(columns=["_key"])
                current = current[cols]
                ws.clear()
                ws.update([current.columns.tolist()]+current.values.tolist())
                st.success("Tallennettu Google Sheetiin!")
            except Exception as e:
                st.error(f"Tallennus epäonnistui: {e}")






















































