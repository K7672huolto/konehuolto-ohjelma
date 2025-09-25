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

# --------- LOGIN (Enterillä) ---------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "login_failed" not in st.session_state:
    st.session_state.login_failed = False

if not st.session_state.logged_in:
    st.title("Kirjaudu sisään")

    # Lomake: Enter painaminen missä tahansa kentässä lähettää lomakkeen
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Käyttäjätunnus", key="login_user")
        password = st.text_input("Salasana", type="password", key="login_pw")
        submitted = st.form_submit_button("Kirjaudu")  # Enter toimii tässä automaattisesti

    if submitted:
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
    # varmista huoltovälisarakkeet olemassa
    for col in ["Huoltoväli_h", "Huoltoväli_pv"]:
        if col not in df.columns:
            df[col] = 0
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

# --- Apufunktio: turvallinen int-muunnos ---
def safe_int(x) -> int:
    """Muunna mitä vain kokonaisluvuksi (pilkut ja pisteet sallittu). Tyhjä -> 0."""
    if x is None:
        return 0
    s = str(x).strip().replace(",", ".")
    try:
        return int(float(s))
    except:
        return 0

huolto_df = lue_huollot()
koneet_df = lue_koneet()
koneet_data = ryhmat_ja_koneet(koneet_df) if not koneet_df.empty else {}

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ Lisää huolto", 
    "📋 Huoltohistoria", 
    "🛠 Koneet ja ryhmät",
    "📊 Käyttötunnit"
])


# ----------- TAB 1: LISÄÄ HUOLTO + ASETUS HUOLTOVÄLEILLE -----------
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
            # --- Näytä koneen nykyiset huoltovälit ---
            nykyinen_h = safe_int(koneet_df.loc[koneet_df["Kone"] == kone_valinta, "Huoltoväli_h"].values[0]) if "Huoltoväli_h" in koneet_df.columns else 0
            nykyinen_pv = safe_int(koneet_df.loc[koneet_df["Kone"] == kone_valinta, "Huoltoväli_pv"].values[0]) if "Huoltoväli_pv" in koneet_df.columns else 0

            st.markdown("#### Huoltovälit (valinnaiset)")
            colh1, colh2 = st.columns(2)
            uusi_h = colh1.number_input("Huoltoväli (tunnit)", min_value=0, step=10, value=nykyinen_h, key="tab1_hv_h")
            uusi_pv = colh2.number_input("Huoltoväli (päivät)", min_value=0, step=30, value=nykyinen_pv, key="tab1_hv_pv")

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
                            # Päivitä myös koneen huoltovälit
                            koneet_df.loc[koneet_df["Kone"] == kone_valinta, "Huoltoväli_h"] = safe_int(uusi_h)
                            koneet_df.loc[koneet_df["Kone"] == kone_valinta, "Huoltoväli_pv"] = safe_int(uusi_pv)
                            tallenna_koneet(koneet_df)

                            st.success("Huolto tallennettu ja huoltovälit päivitetty!")
                            st.rerun()
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

        # --- Järjestys esikatseluun ---
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

                # --- Päivitä / lisää myös Käyttötunnit-sheet (kevyt päivitys) ---
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
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet

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


# ----------- TAB 3: KONEET JA RYHMÄT (+ HUOLTOVÄLIT) -----------
with tab3:
    st.header("Koneiden ja ryhmien hallinta")

    for col in ["Huoltoväli_h", "Huoltoväli_pv"]:
        if col not in koneet_df.columns:
            koneet_df[col] = 0

    st.subheader("Lisää kone")
    ryhma_vaihtoehdot = list(koneet_data.keys()) + ["Uusi ryhmä"] if len(koneet_data) > 0 else ["Uusi ryhmä"]
    valittu_ryhma_uusi = st.selectbox("Ryhmän valinta tai luonti", ryhma_vaihtoehdot, key="tab3_ryhma_add")
    kaytettava_ryhma = st.text_input("Uuden ryhmän nimi", key="tab3_new_group") if valittu_ryhma_uusi == "Uusi ryhmä" else valittu_ryhma_uusi

    col_add1, col_add2, col_add3, col_add4 = st.columns([0.28, 0.2, 0.22, 0.3])
    with col_add1:
        uusi_nimi = st.text_input("Koneen nimi", key="tab3_kone_nimi")
    with col_add2:
        uusi_id = st.text_input("Koneen ID-numero", key="tab3_kone_id")
    with col_add3:
        hv_h = st.number_input("Huoltoväli (tunnit)", min_value=0, step=10, value=0, key="tab3_hv_h_add")
    with col_add4:
        hv_pv = st.number_input("Huoltoväli (päivät)", min_value=0, step=30, value=0, key="tab3_hv_pv_add")

    if st.button("➕ Lisää kone", key="tab3_lisaa_kone"):
        if kaytettava_ryhma and uusi_nimi and uusi_id:
            uusi = pd.DataFrame([{
                "Kone": uusi_nimi,
                "ID": uusi_id,
                "Ryhmä": kaytettava_ryhma,
                "Huoltoväli_h": safe_int(hv_h),
                "Huoltoväli_pv": safe_int(hv_pv),
            }])
            uusi_koneet_df = pd.concat([koneet_df, uusi], ignore_index=True)
            tallenna_koneet(uusi_koneet_df)
            st.success(f"Kone {uusi_nimi} lisätty ryhmään {kaytettava_ryhma} (hv_h={safe_int(hv_h)}, hv_pv={safe_int(hv_pv)})")
            st.rerun()
        else:
            st.warning("Täytä vähintään ryhmä, koneen nimi ja ID.")

    st.markdown("---")

    st.subheader("Muokkaa koneen huoltovälejä")
    if not koneet_df.empty:
        muok_ryhma = st.selectbox("Valitse ryhmä", sorted(koneet_df["Ryhmä"].unique().tolist()), key="tab3_edit_group")
        koneet_muok = koneet_df[koneet_df["Ryhmä"] == muok_ryhma]
        if not koneet_muok.empty:
            muok_kone = st.selectbox("Valitse kone", koneet_muok["Kone"].tolist(), key="tab3_edit_machine")
            rivi = koneet_df[koneet_df["Kone"] == muok_kone].iloc[0]

            col_e1, col_e2, col_e3 = st.columns([0.35, 0.25, 0.4])
            with col_e1:
                cur_h = safe_int(rivi.get("Huoltoväli_h", 0))
                new_h = st.number_input("Huoltoväli (tunnit)", min_value=0, step=10, value=cur_h, key="tab3_hv_h_edit")
            with col_e2:
                cur_pv = safe_int(rivi.get("Huoltoväli_pv", 0))
                new_pv = st.number_input("Huoltoväli (päivät)", min_value=0, step=30, value=cur_pv, key="tab3_hv_pv_edit")
            with col_e3:
                st.write(" ")
                if st.button("💾 Tallenna huoltovälit", key="tab3_save_intervals"):
                    koneet_df.loc[koneet_df["Kone"] == muok_kone, "Huoltoväli_h"] = safe_int(new_h)
                    koneet_df.loc[koneet_df["Kone"] == muok_kone, "Huoltoväli_pv"] = safe_int(new_pv)
                    tallenna_koneet(koneet_df)
                    st.success(f"Päivitetty: {muok_kone} → hv_h={safe_int(new_h)}, hv_pv={safe_int(new_pv)}")
                    st.rerun()
        else:
            st.info("Valitussa ryhmässä ei ole koneita.")
    else:
        st.info("Ei koneita muokattavaksi.")

    st.markdown("---")

    st.subheader("Poista kone")
    if not koneet_df.empty:
        poisto_ryhma = st.selectbox("Valitse ryhmä (poistoa varten)", sorted(koneet_df["Ryhmä"].unique().tolist()), key="tab3_poistoryhma")
        koneet_poisto = koneet_df[koneet_df["Ryhmä"] == poisto_ryhma]
        if not koneet_poisto.empty:
            poisto_nimi = st.selectbox("Valitse kone", koneet_poisto["Kone"].tolist(), key="tab3_poistokone")
            if st.button("🗑️ Poista kone", key="tab3_poista_kone"):
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
        ryhma_valinta = st.selectbox("Näytä koneet ryhmästä", sorted(koneet_df["Ryhmä"].unique().tolist()), key="tab3_list_group")
        koneet_listattavaan = koneet_df[koneet_df["Ryhmä"] == ryhma_valinta]
        if not koneet_listattavaan.empty:
            st.table(koneet_listattavaan[["Kone", "ID", "Huoltoväli_h", "Huoltoväli_pv"]])
        else:
            st.info("Ryhmässä ei koneita.")
    else:
        st.info("Ei ryhmiä.")



# ----------- TAB 4: KÄYTTÖTUNNIT + HUOLTOVÄLI MUISTUTUKSET + PDF -----------
with tab4:
    st.header("Kaikkien koneiden käyttötunnit, erotus ja muistutukset")

    # CSS
    st.markdown("""
    <style>
      div[data-testid="stNumberInput"] input::-webkit-outer-spin-button,
      div[data-testid="stNumberInput"] input::-webkit-inner-spin-button {
          -webkit-appearance: none !important;
          margin: 0 !important;
      }
      div[data-testid="stNumberInput"] input[type=number] {
          -moz-appearance: textfield !important;
      }
      div[data-testid="stNumberInput"] button { display: none !important; }
      div[data-testid="stNumberInput"] div[role="button"],
      div[data-testid="stNumberInput"] svg { display: none !important; }
      div[data-testid="stNumberInput"] input { text-align: left; }
      .tab4-table-header { font-weight: 600; padding: 4px 0; }
      .tab4-cell { padding: 2px 0; }
    </style>
    """, unsafe_allow_html=True)

    # --- Aputoiminnot ---
    def lue_kayttotunnit_sheet_df() -> pd.DataFrame:
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
        if df_kaytto.empty:
            return {}
        tmp = df_kaytto.copy()
        tmp["aika_dt"] = pd.to_datetime(tmp["Aika"], dayfirst=True, errors="coerce")
        tmp.sort_values("aika_dt", ascending=True, inplace=True)
        last_rows = tmp.groupby("Kone", as_index=False).tail(1)
        return {str(r["Kone"]): safe_int(r.get("Uudet tunnit", 0)) for _, r in last_rows.iterrows()}

    def viimeisin_huolto_koneelle(df_huollot: pd.DataFrame, kone_nimi: str):
        sub = df_huollot[df_huollot["Kone"] == kone_nimi].copy()
        if sub.empty:
            return "-", 0
        sub["pvm_dt"] = pd.to_datetime(sub["Päivämäärä"], dayfirst=True, errors="coerce")
        sub = sub.sort_values("pvm_dt", ascending=False)
        return sub.iloc[0].get("Päivämäärä", "-"), safe_int(sub.iloc[0].get("Tunnit", 0))

    # Ei koneita
    if koneet_df.empty:
        st.info("Ei koneita lisättynä.")
        st.stop()

    # Lue sheetit
    kaytto_df = lue_kayttotunnit_sheet_df()
    viimeisin_uudet_map = hae_viimeisin_uusi_tunti_map(kaytto_df)

    # Rakenna näkymärivit
    rivit = []
    for _, row in koneet_df.iterrows():
        kone = str(row["Kone"])
        ryhma = str(row.get("Ryhmä", ""))
        hv_h = safe_int(row.get("Huoltoväli_h", 0))
        hv_pv = safe_int(row.get("Huoltoväli_pv", 0))

        pvm, viimeisin_tunnit = viimeisin_huolto_koneelle(huolto_df, kone)
        default_uudet = viimeisin_uudet_map.get(kone, viimeisin_tunnit)

        rivit.append({
            "Kone": kone,
            "Ryhmä": ryhma,
            "Viimeisin huolto (pvm)": pvm,
            "Viimeisin huolto (tunnit)": viimeisin_tunnit,
            "Huoltoväli_h": hv_h,
            "Huoltoväli_pv": hv_pv,
            "Syötä uudet tunnit (default)": default_uudet,
        })
    df_tunnit = pd.DataFrame(rivit)

    if "tab4_inputs" not in st.session_state:
        st.session_state.tab4_inputs = {}

    # Otsikkorivi
    colw = [0.18,0.1,0.13,0.1,0.08,0.08,0.13,0.1]  
    headers = ["Kone","Ryhmä","Viimeisin huolto (pvm)","Viimeisin huolto (tunnit)",
               "Huoltoväli_h","Huoltoväli_pv","Syötä uudet tunnit","Erotus"]
    cols = st.columns(colw, gap="small")
    for j, h in enumerate(headers):
        cols[j].markdown(f"<div class='tab4-table-header'>{h}</div>", unsafe_allow_html=True)

    # Rivien tulostus
    for i, r in df_tunnit.iterrows():
        c = st.columns(colw, gap="small")
        kone_n, ryhma, pvm = r["Kone"], r["Ryhmä"], r["Viimeisin huolto (pvm)"]
        ed, hv_h, hv_pv = r["Viimeisin huolto (tunnit)"], r["Huoltoväli_h"], r["Huoltoväli_pv"]

        state_key = f"tab4_uudet_{i}"
        default_uudet = st.session_state.tab4_inputs.get(state_key, safe_int(r["Syötä uudet tunnit (default)"]))
        uudet = c[6].number_input("", min_value=0, step=1, value=int(default_uudet), key=f"tab4_num_{i}")
        st.session_state.tab4_inputs[state_key] = uudet
        erotus = safe_int(uudet) - ed

        muistutus = ""
        if hv_pv > 0 and pvm != "-":
            try:
                viimeisin_pvm = datetime.strptime(pvm, "%d.%m.%Y")
                paivia_kulunut = (datetime.today() - viimeisin_pvm).days
                if paivia_kulunut >= hv_pv:
                    muistutus = f"⚠️ {paivia_kulunut} pv (yli {hv_pv})"
            except:
                pass

        c[0].markdown(f"<div class='tab4-cell'><b>{kone_n}</b></div>", unsafe_allow_html=True)
        c[1].markdown(f"<div class='tab4-cell'>{ryhma}</div>", unsafe_allow_html=True)
        c[2].markdown(f"<div class='tab4-cell'>{pvm}</div>", unsafe_allow_html=True)
        c[3].markdown(f"<div class='tab4-cell'>{ed}</div>", unsafe_allow_html=True)
        c[4].markdown(f"<div class='tab4-cell'>{hv_h}</div>", unsafe_allow_html=True)
        c[5].markdown(f"<div class='tab4-cell'>{hv_pv}</div>", unsafe_allow_html=True)

        if hv_h > 0 and erotus >= hv_h:
            c[7].markdown(f"<div class='tab4-cell' style='color:#d00;'>⚠️ {erotus}</div>", unsafe_allow_html=True)
        else:
            c[7].markdown(f"<div class='tab4-cell'>{erotus}</div>", unsafe_allow_html=True)

        if muistutus:
            c[2].markdown(f"<div class='tab4-cell' style='color:#d00;'>{pvm} {muistutus}</div>", unsafe_allow_html=True)

        df_tunnit.at[i,"Syötä uudet tunnit"] = safe_int(uudet)
        df_tunnit.at[i,"Erotus"] = erotus
        df_tunnit.at[i,"Muistutus"] = muistutus

    # --- Tallenna ---
    if st.button("💾 Tallenna kaikkien koneiden tunnit ja muistutukset", key="tab4_save_all"):
        try:
            ws = get_gsheet_connection("Käyttötunnit")
            nyt = datetime.today().strftime("%d.%m.%Y %H:%M")
            header = ["Aika","Kone","Ryhmä","Edellinen huolto","Uudet tunnit","Erotus"]
            body = []
            for _, r in df_tunnit.iterrows():
                body.append([
                    nyt, r["Kone"], r["Ryhmä"], safe_int(r["Viimeisin huolto (tunnit)"]),
                    safe_int(r.get("Syötä uudet tunnit",0)), safe_int(r.get("Erotus",0))
                ])
            ws.clear()
            ws.update([header] + body)
            st.success("Tallennettu Käyttötunnit-välilehdelle!")
        except Exception as e:
            st.error(f"Tallennus epäonnistui: {e}")

    # --- PDF ---
    def make_pdf_bytes(df: pd.DataFrame):
        buf = BytesIO()
        otsikkotyyli = ParagraphStyle(name="otsikko", fontName="Helvetica-Bold", fontSize=16)
        paivays = Paragraph(datetime.today().strftime("%d.%m.%Y"),
                            ParagraphStyle("date", fontSize=12, alignment=2))
        otsikko = Paragraph("Koneiden käyttötunnit ja huoltomuistutukset", otsikkotyyli)

        cols = ["Kone","Ryhmä","Viimeisin huolto (pvm)","Viimeisin huolto (tunnit)",
                "Huoltoväli_h","Huoltoväli_pv","Uudet tunnit","Erotus","Muistutus"]
        data = [cols]

        for _, r in df.iterrows():
            k = Paragraph(f"<b>{str(r['Kone'])}</b>",
                          ParagraphStyle(name="kb", fontName="Helvetica-Bold", fontSize=9))
            ry = str(r["Ryhmä"])
            pv = str(r["Viimeisin huolto (pvm)"])
            ed = safe_int(r["Viimeisin huolto (tunnit)"])
            hvh = safe_int(r["Huoltoväli_h"])
            hvp = safe_int(r["Huoltoväli_pv"])
            uu = safe_int(r.get("Syötä uudet tunnit", 0))
            er = safe_int(r.get("Erotus", 0))
            muistutus = str(r.get("Muistutus",""))

            if hvh > 0 and er >= hvh:
                er_cell = Paragraph(f"<font color='red'>⚠️ {er}</font>",
                                    ParagraphStyle(name="red", fontName="Helvetica", fontSize=9))
            else:
                er_cell = Paragraph(str(er), ParagraphStyle(name="norm", fontName="Helvetica", fontSize=9))

            muistutus_cell = Paragraph(
                f"<font color='red'>{muistutus}</font>" if muistutus else "",
                ParagraphStyle(name="m", fontName="Helvetica", fontSize=9)
            )

            data.append([k, ry, pv, str(ed), str(hvh), str(hvp), str(uu), er_cell, muistutus_cell])

        col_widths = [120, 80, 100, 80, 70, 70, 80, 70, 120]
        table = Table(data, repeatRows=1, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.teal),
            ('TEXTCOLOR',  (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0,0), (-1,-1), 8),
            ('GRID',       (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
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

    st.download_button(
        "⬇️ Lataa PDF-tiedosto",
        data=make_pdf_bytes(df_tunnit.copy()),
        file_name="koneiden_tunnit_muistutuksilla.pdf",
        mime="application/pdf",
        type="secondary",
        key="tab4_pdf_dl"
    )





