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
            # Koneen nimi ensin, sitten ID (sulkeissa)
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
                # HUOM: Huoltokohteet voivat olla kaikki "--"
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


# --- Huoltohistoria + Muokkaus + PDF ---
with tab2:
    st.header("Huoltohistoria")
    if huolto_df.empty or huolto_df["Kone"].dropna().empty:
        st.info("Ei huoltoja tallennettu vielä.")
    else:
        df = huolto_df.copy()
        df = df.reset_index(drop=True)

        # --- Ryhmän ja koneen suodatus ---
        kaikki_ryhmat = ["Kaikki"] + sorted([r for r in df["Ryhmä"].dropna().unique() if r])
        valittu_ryhma = st.selectbox("Suodata ryhmän mukaan", kaikki_ryhmat, index=0, key="ryhma_suodatin_tab2")
        df_ryhma = df if valittu_ryhma == "Kaikki" else df[df["Ryhmä"] == valittu_ryhma]

        kaikki_koneet = ["Kaikki"] + sorted([k for k in df_ryhma["Kone"].dropna().unique() if k])
        valittu_kone = st.selectbox("Suodata koneen mukaan", kaikki_koneet, index=0, key="kone_suodatin_tab2")
        df_kone = df_ryhma if valittu_kone == "Kaikki" else df_ryhma[df_ryhma["Kone"] == valittu_kone]

        # Käytetään jatkossa vain suodatettua df_kone:a
        df = df_kone.reset_index(drop=True)

        # ✔-LOGIIKKA
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
        if st.button("Lataa PDF", key="pdf_tab2"):
            pdfdata = lataa_pdf(df_naytto)
            st.download_button(
                label="Lataa PDF-tiedosto",
                data=pdfdata,
                file_name="huoltohistoria.pdf",
                mime="application/pdf",
                key="pdf_dl_tab2"
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
