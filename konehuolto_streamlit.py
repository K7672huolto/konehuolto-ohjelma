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
with tab4:
    st.header("Kaikkien koneiden käyttötunnit ja erotus")

    # Piilota number_inputin ±-nuolet ja pakota vasen tasaus
    st.markdown("""
    <style>
      /* Piilota st.number_input up/down-napit (WebKit + Firefox) */
      div[data-testid="stNumberInput"] input::-webkit-outer-spin-button,
      div[data-testid="stNumberInput"] input::-webkit-inner-spin-button {
          -webkit-appearance: none !important;
          margin: 0 !important;
      }
      div[data-testid="stNumberInput"] input[type=number] {
          -moz-appearance: textfield !important;
      }
      /* Vasen tasaus syöttökenttään */
      div[data-testid="stNumberInput"] input {
          text-align: left;
      }
      /* Kevyt taulukkutyyli */
      .tab4-table-header { font-weight: 600; padding: 4px 0; }
      .tab4-cell { padding: 2px 0; }
    </style>
    """, unsafe_allow_html=True)

    # Apurit
    def safe_int(x) -> int:
        """Muunna mitä vain kokonaisluvuksi (pilkut ja pisteet sallittu). Tyhjä -> 0."""
        if x is None:
            return 0
        s = str(x).strip().replace(",", ".")
        try:
            return int(float(s))
        except:
            return 0

    def viimeisin_huolto_koneelle(df_huollot: pd.DataFrame, kone_nimi: str):
        """Palauta (pvm_str, tunnit_int) koneen uusimman huollon mukaan."""
        sub = df_huollot[df_huollot["Kone"] == kone_nimi].copy()
        if sub.empty:
            return "-", 0
        sub["pvm_dt"] = pd.to_datetime(sub["Päivämäärä"], dayfirst=True, errors="coerce")
        sub = sub.sort_values("pvm_dt", ascending=False)
        pvm = sub.iloc[0].get("Päivämäärä", "-")
        tunnit = safe_int(sub.iloc[0].get("Tunnit", 0))
        return pvm, tunnit

    def lue_kayttotunnit_sheet_df() -> pd.DataFrame:
        """Lue Käyttötunnit-välilehti. Jos tyhjä/puuttuu, palauta tyhjä df oikeilla otsikoilla."""
        try:
            ws = get_gsheet_connection("Käyttötunnit")
            data = ws.get_all_records()
            if not data:
                return pd.DataFrame(columns=["Aika","Kone","Ryhmä","Edellinen huolto","Uudet tunnit","Erotus"])
            dfk = pd.DataFrame(data)
            for col in ["Aika","Kone","Ryhmä","Edellinen huolto","Uudet tunnit","Erotus"]:
                if col not in dfk.columns:
                    dfk[col] = ""
            return dfk
        except Exception:
            return pd.DataFrame(columns=["Aika","Kone","Ryhmä","Edellinen huolto","Uudet tunnit","Erotus"])

    def hae_viimeisin_uusi_tunti_map(df_kaytto: pd.DataFrame) -> dict:
        """Palauta {Kone: viimeisin 'Uudet tunnit'} sheetiltä (Aika uusimmasta)."""
        if df_kaytto.empty:
            return {}
        tmp = df_kaytto.copy()
        tmp["aika_dt"] = pd.to_datetime(tmp["Aika"], dayfirst=True, errors="coerce")
        tmp.sort_values("aika_dt", ascending=True, inplace=True)
        last_rows = tmp.groupby("Kone", as_index=False).tail(1)
        m = {}
        for _, r in last_rows.iterrows():
            m[str(r["Kone"])] = safe_int(r.get("Uudet tunnit", 0))
        return m

    # Ei koneita -> info
    if koneet_df.empty:
        st.info("Ei koneita lisättynä.")
        st.stop()

    # Lue viimeksi tallennetut käyttötunnit sheetiltä
    kaytto_df = lue_kayttotunnit_sheet_df()
    viimeisin_uudet_map = hae_viimeisin_uusi_tunti_map(kaytto_df)

    # Rakenna näkymärivit
    koneet_nimet = koneet_df["Kone"].tolist()
    rivit = []
    for kone in koneet_nimet:
        ryhma = koneet_df.loc[koneet_df["Kone"] == kone, "Ryhmä"].values[0] if "Ryhmä" in koneet_df.columns else ""
        pvm, viimeisin_tunnit = viimeisin_huolto_koneelle(huolto_df, kone)
        default_uudet = viimeisin_uudet_map.get(kone, viimeisin_tunnit)
        rivit.append({
            "Kone": kone,
            "Ryhmä": ryhma,
            "Viimeisin huolto (pvm)": pvm,
            "Viimeisin huolto (tunnit)": viimeisin_tunnit,
            "Syötä uudet tunnit (default)": safe_int(default_uudet),
        })
    df_tunnit = pd.DataFrame(rivit)

    # Pidetään käyttäjän rivikohtaiset syötteet sessiossa
    if "tab4_inputs" not in st.session_state:
        st.session_state.tab4_inputs = {}

    # Otsikkorivi (yksi taulukko)
    colw = [0.24, 0.16, 0.14, 0.14, 0.16, 0.16]  # suhteelliset leveydet
    cols = st.columns(colw, gap="small")
    cols[0].markdown("<div class='tab4-table-header'>Kone</div>", unsafe_allow_html=True)
    cols[1].markdown("<div class='tab4-table-header'>Ryhmä</div>", unsafe_allow_html=True)
    cols[2].markdown("<div class='tab4-table-header'>Viimeisin huolto (pvm)</div>", unsafe_allow_html=True)
    cols[3].markdown("<div class='tab4-table-header'>Viimeisin huolto (tunnit)</div>", unsafe_allow_html=True)
    cols[4].markdown("<div class='tab4-table-header'>Syötä uudet tunnit</div>", unsafe_allow_html=True)
    cols[5].markdown("<div class='tab4-table-header'>Erotus</div>", unsafe_allow_html=True)

    # Rivien piirtäminen
    for i, row in df_tunnit.iterrows():
        c = st.columns(colw, gap="small")

        kone_n = str(row["Kone"])
        ryhma  = str(row["Ryhmä"])
        pvm    = str(row["Viimeisin huolto (pvm)"])
        ed     = safe_int(row["Viimeisin huolto (tunnit)"])

        state_key = f"tab4_uudet_{i}"
        default_uudet = st.session_state.tab4_inputs.get(state_key, safe_int(row["Syötä uudet tunnit (default)"]))

        # Solut (kone bold)
        c[0].markdown(f"<div class='tab4-cell'><b>{kone_n}</b></div>", unsafe_allow_html=True)
        c[1].markdown(f"<div class='tab4-cell'>{ryhma}</div>", unsafe_allow_html=True)
        c[2].markdown(f"<div class='tab4-cell'>{pvm}</div>", unsafe_allow_html=True)
        c[3].markdown(f"<div class='tab4-cell'>{ed}</div>", unsafe_allow_html=True)

        # Syöttö: kokonaisluvut, ±-nuolet piilotettu CSS:llä
        uudet = c[4].number_input(
            label="",
            min_value=0,
            step=1,
            value=int(default_uudet),
            key=f"tab4_num_{i}"
        )
        st.session_state.tab4_inputs[state_key] = uudet

        erotus = safe_int(uudet) - ed
        c[5].markdown(f"<div class='tab4-cell' style='color:#d00;'>{erotus}</div>", unsafe_allow_html=True)

        # Päivitetään DataFrame tallennusta/PDF:ää varten
        df_tunnit.at[i, "Syötä uudet tunnit"] = safe_int(uudet)
        df_tunnit.at[i, "Erotus"] = erotus

    # --- Tallenna kaikki (korvaa koko sheet) & PDF ---
    col_save, col_pdf = st.columns([0.4, 0.6])

    if col_save.button("💾 Tallenna kaikkien koneiden tunnit", key="tab4_save_all"):
        try:
            ws = get_gsheet_connection("Käyttötunnit")
            nyt = datetime.today().strftime("%d.%m.%Y %H:%M")

            header = ["Aika", "Kone", "Ryhmä", "Edellinen huolto", "Uudet tunnit", "Erotus"]
            body = []
            for _, r in df_tunnit.iterrows():
                body.append([
                    nyt,
                    str(r["Kone"]),
                    str(r["Ryhmä"]),
                    safe_int(r["Viimeisin huolto (tunnit)"]),
                    safe_int(r.get("Syötä uudet tunnit", 0)),
                    safe_int(r.get("Erotus", 0)),
                ])

            # Yksi tyhjennys + yksi update (minimoi write-pyynnöt)
            ws.clear()
            ws.update([header] + body)

            st.success("Tallennettu Käyttötunnit-välilehdelle!")
        except Exception as e:
            st.error(f"Tallennus epäonnistui: {e}")

    # PDF-lataus
    def make_pdf_bytes(df):
        buf = BytesIO()
        otsikkotyyli = ParagraphStyle(name="otsikko", fontName="Helvetica-Bold", fontSize=16)
        paivays = Paragraph(datetime.today().strftime("%d.%m.%Y"), ParagraphStyle("date", fontSize=12, alignment=2))
        otsikko = Paragraph("Kaikkien koneiden käyttötunnit ja erotus", otsikkotyyli)

        cols = ["Kone","Ryhmä","Viimeisin huolto (pvm)","Viimeisin huolto (tunnit)","Syötä uudet tunnit","Erotus"]
        data = [cols]
        for _, r in df.iterrows():
            k  = Paragraph(f"<b>{str(r['Kone'])}</b>", ParagraphStyle(name="kb", fontName="Helvetica-Bold", fontSize=9))
            ry = str(r["Ryhmä"])
            pv = str(r["Viimeisin huolto (pvm)"])
            ed = safe_int(r["Viimeisin huolto (tunnit)"])
            uu = safe_int(r.get("Syötä uudet tunnit", 0))
            er = safe_int(r.get("Erotus", 0))
            er_cell = Paragraph(f"<font color='red'>{er}</font>", ParagraphStyle(name="red", fontName="Helvetica", fontSize=9))
            data.append([k, ry, pv, f"{ed:d}", f"{uu:d}", er_cell])

        col_widths = [170, 120, 120, 110, 110, 80]
        table = Table(data, repeatRows=1, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.teal),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 9),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN',      (0,0), (-1,-1), 'LEFT'),  # vasen tasaus
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ]))

        def footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(420, 20, f"Sivu {doc.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            buf, pagesize=landscape(A4),
            rightMargin=0.5*inch, leftMargin=0.5*inch,
            topMargin=0.7*inch, bottomMargin=0.5*inch
        )
        doc.build(
            [Spacer(1, 4*mm),
             Table([[otsikko, paivays]], colWidths=[340, 340], style=[
                 ("ALIGN", (0,0), (0,0), "LEFT"),
                 ("ALIGN", (1,0), (1,0), "RIGHT"),
                 ("VALIGN", (0,0), (-1,-1), "TOP"),
                 ("BOTTOMPADDING", (0,0), (-1,-1), 0),
                 ("TOPPADDING",   (0,0), (-1,-1), 0),
             ]),
             Spacer(1, 4*mm),
             table],
            onFirstPage=footer,
            onLaterPages=footer
        )
        return buf.getvalue()

    col_pdf.download_button(
        "⬇️ Lataa PDF-tiedosto",
        data=make_pdf_bytes(df_tunnit.copy()),
        file_name="kaikkien_koneiden_tunnit.pdf",
        mime="application/pdf",
        type="secondary",
        key="tab4_pdf_dl"
    )


































































































