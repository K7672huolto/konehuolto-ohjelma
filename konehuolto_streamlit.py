import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from PIL import Image
import base64

EXCEL_TIEDOSTO = "konehuollot.xlsx"
KONEET_TIEDOSTO = "koneet.json"

st.set_page_config(page_title="Konehuolto", layout="wide")
st.markdown("""
    <style>
    .block-container {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    </style>
""", unsafe_allow_html=True)

def alusta_koneet_json():
    if not os.path.exists(KONEET_TIEDOSTO):
        esimerkki = {
            "Traktorit": [{"nimi": "Valtra N123", "id": "1"}],
            "Leikkurit": [{"nimi": "Toro 3200", "id": "2"}]
        }
        with open(KONEET_TIEDOSTO, "w", encoding="utf-8") as f:
            json.dump(esimerkki, f, ensure_ascii=False, indent=2)

def alusta_excel():
    if not os.path.exists(EXCEL_TIEDOSTO):
        sarakkeet = [
            "Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti",
            "MÖ", "HÖ", "AÖ", "IS",
            "MS", "HS", "R", "PS",
            "T", "VÖ", "PÖ"
        ]
        pd.DataFrame(columns=sarakkeet).to_excel(EXCEL_TIEDOSTO, index=False)

def lue_koneet():
    with open(KONEET_TIEDOSTO, "r", encoding="utf-8") as f:
        return json.load(f)

def tallenna_koneet(data):
    with open(KONEET_TIEDOSTO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def lue_data():
    return pd.read_excel(EXCEL_TIEDOSTO)

def tallenna_data(df):
    sarakkeet = list(df.columns)
    if "ID" in sarakkeet:
        sarakkeet.remove("ID")
        sarakkeet.insert(1, "ID")
    df = df.reindex(columns=sarakkeet)
    df.to_excel(EXCEL_TIEDOSTO, index=False)

def konekohtainen_naytto_nimi_id_samalle_riville(df, huolto_kohteet):
    if df.empty:
        return pd.DataFrame([], columns=["Rivi"] + [c for c in df.columns if c != "ID"]), []
    df2 = df.copy()
    columns = ["Rivi"] + [c for c in df2.columns if c != "ID"]
    uudet_rivit = []
    index_map = []
    rivinro = 1
    viime_kone = None
    viime_id = None
    koneen_huollot = []
    buffer_idxs = []

    def pure_koneen_huollot():
        nonlocal rivinro
        if not koneen_huollot:
            return
        # Ensimmäinen huolto: koneen nimi + tiedot
        r = {col: koneen_huollot[0][col] for col in columns if col != "Rivi"}
        for kohta in huolto_kohteet:
            val = str(koneen_huollot[0].get(kohta, "--")).strip()
            if val.lower() == "ok":
                r[kohta] = "✅"
            elif val == "" or val.lower() == "nan":
                r[kohta] = "--"
            else:
                r[kohta] = val
        r["Kone"] = koneen_huollot[0]["Kone"]
        rivi = {"Rivi": rivinro}
        rivi.update(r)
        uudet_rivit.append(rivi)
        index_map.append(buffer_idxs[0])
        rivinro += 1
        # Toinen huolto (jos on): id + tiedot
        if len(koneen_huollot) > 1:
            r2 = {col: koneen_huollot[1][col] for col in columns if col != "Rivi"}
            for kohta in huolto_kohteet:
                val = str(koneen_huollot[1].get(kohta, "--")).strip()
                if val.lower() == "ok":
                    r2[kohta] = "✅"
                elif val == "" or val.lower() == "nan":
                    r2[kohta] = "--"
                else:
                    r2[kohta] = val
            kone_id = str(koneen_huollot[1]["ID"]) if "ID" in koneen_huollot[1] else ""
            r2["Kone"] = kone_id
            rivi2 = {"Rivi": rivinro}
            rivi2.update(r2)
            uudet_rivit.append(rivi2)
            index_map.append(buffer_idxs[1])
            rivinro += 1
        # Mahdolliset lisähuollot: tyhjä Kone-sarake
        for i in range(2, len(koneen_huollot)):
            r3 = {col: koneen_huollot[i][col] for col in columns if col != "Rivi"}
            for kohta in huolto_kohteet:
                val = str(koneen_huollot[i].get(kohta, "--")).strip()
                if val.lower() == "ok":
                    r3[kohta] = "✅"
                elif val == "" or val.lower() == "nan":
                    r3[kohta] = "--"
                else:
                    r3[kohta] = val
            r3["Kone"] = ""
            rivi3 = {"Rivi": rivinro}
            rivi3.update(r3)
            uudet_rivit.append(rivi3)
            index_map.append(buffer_idxs[i])
            rivinro += 1

    for idx, row in df2.iterrows():
        kone = row["Kone"]
        if viime_kone is not None and kone != viime_kone:
            # Tyhjä rivi
            empty_row = {col: "" for col in columns if col != "Rivi"}
            rivi = {"Rivi": rivinro}
            rivi.update(empty_row)
            uudet_rivit.append(rivi)
            index_map.append(None)
            rivinro += 1
            # Purkaus
            pure_koneen_huollot()
            koneen_huollot = []
            buffer_idxs = []
        viime_kone = kone
        viime_id = str(row["ID"]) if "ID" in row else ""
        koneen_huollot.append(row)
        buffer_idxs.append(idx)
    # Viimeinen kone
    pure_koneen_huollot()

    return pd.DataFrame(uudet_rivit, columns=columns), index_map

def taustakuva_local(filename):
    with open(filename, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return f"data:image/jpg;base64,{encoded}"

alusta_koneet_json()
alusta_excel()
koneet = lue_koneet()
df = lue_data()


st.markdown("---")

tab1, tab2, tab3 = st.tabs(["➕ Lisää huolto", "📋 Huoltohistoria", "🛠 Koneet ja ryhmät"])

with tab1:
    st.header("Lisää uusi huoltotapahtuma")
    koneet_data = lue_koneet()
    ryhmat_lista = sorted(list(koneet_data.keys()))
    valittu_ryhma = st.selectbox("Ryhmä", ryhmat_lista, key="ryhma_selectbox")
    koneet_ryhmaan = koneet_data[valittu_ryhma] if valittu_ryhma else []

    # Session state tallennettu & kenttien nollaus
    if "tallennettu" not in st.session_state:
        st.session_state.tallennettu = False

    if st.session_state.tallennettu:
        st.success("Tallennettu!")
        st.session_state.kayttotunnit = ""
        st.session_state.vapaa = ""
        for kohta in [
            "MÖ", "HÖ", "AÖ", "IS",
            "MS", "HS", "R", "PS",
            "T", "VÖ", "P"
        ]:
            st.session_state[f"valinta_{kohta}"] = "--"
        st.session_state.tallennettu = False

    if koneet_ryhmaan:
        koneet_df = pd.DataFrame(koneet_ryhmaan)
        koneet_df["valinta"] = koneet_df["nimi"] + " (ID: " + koneet_df["id"].astype(str) + ")"
        kone_valinta = st.radio(
            "Valitse kone:",
            koneet_df["valinta"].tolist(),
            key="konevalinta_radio",
            index=0 if len(koneet_df) > 0 else None
        )
        valittu_kone_nimi = kone_valinta.split(" (ID:")[0]
        kone_id = koneet_df[koneet_df["nimi"] == valittu_kone_nimi]["id"].values[0]
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
        huolto_kohteet = [
            "Moottoriöljy", "Hydrauliöljy", "Akseliöljy", "Ilmansuodatin",
            "Moottoriöljyn suodatin", "Hydrauli suodatin", "Rasvaus", "Polttoaine suodatin",
            "Tulpat", "Vaihdelaatikko öljy", "Peräöljy"
        ]
        vaihtoehdot = ["--", "Vaihd", "Tark", "OK", "Muu"]
        valinnat = {}
        cols_huolto = st.columns(6)
        for i, kohta in enumerate(huolto_kohteet):
            with cols_huolto[i % 6]:
                valinnat[kohta] = st.selectbox(
                    f"{kohta}:", vaihtoehdot,
                    key=f"valinta_{kohta}",
                    index=vaihtoehdot.index(st.session_state.get(f"valinta_{kohta}", "--"))
                )
        vapaa = st.text_input("Vapaa teksti", key="vapaa")

        if st.button("Tallenna huolto"):
            if not valittu_ryhma or not valittu_kone_nimi or not kayttotunnit or not kone_id:
                st.warning("Täytä kaikki kentät!")
            else:
                sarakkeet = list(df.columns)
                uusi = {col: "" for col in sarakkeet}
                uusi["Kone"] = valittu_kone_nimi
                uusi["ID"] = kone_id
                uusi["Ryhmä"] = valittu_ryhma
                uusi["Tunnit"] = kayttotunnit
                uusi["Päivämäärä"] = pvm.strftime("%d.%m.%Y")
                uusi["Vapaa teksti"] = vapaa
                for kohta in huolto_kohteet:
                    uusi[kohta] = valinnat[kohta]
                df = pd.concat([df, pd.DataFrame([uusi])], ignore_index=True)
                tallenna_data(df)
                st.session_state.tallennettu = True
                st.rerun()

with tab2:
    st.markdown("### Huoltohistoria")
    huolto_kohteet = [
        "MÖ", "HÖ", "AÖ", "IS",
        "MS", "HS", "R", "PS",
        "T", "VÖ", "PÖ"
    ]
    esikatselu_sarakkeet = [
        "Rivi", "Kone", "Ryhmä", "Tunnit", "Päivämäärä", "Vapaa teksti"
    ] + huolto_kohteet

    koneet_json = lue_koneet()
    ryhmat = list(koneet_json.keys())
    valittu_ryhma = st.selectbox("Suodata ryhmän mukaan", ["Kaikki"] + ryhmat, key="ryhma_selectbox_tab2")
    if valittu_ryhma == "Kaikki":
        filtered_df = df.copy()
        kaikki_koneet_jarjestyksessa = []
        for ryhma in koneet_json:
            for kone in koneet_json[ryhma]:
                kaikki_koneet_jarjestyksessa.append(kone["nimi"])
        koneet_nimet = [nimi for nimi in kaikki_koneet_jarjestyksessa if nimi in set(filtered_df["Kone"].dropna())]
    else:
        filtered_df = df[df["Ryhmä"] == valittu_ryhma]
        koneet_nimet = [k["nimi"] for k in koneet_json[valittu_ryhma]]

    valittu_kone = st.selectbox("Suodata koneen mukaan", ["Kaikki"] + koneet_nimet, key="kone_selectbox_tab2")
    if valittu_kone == "Kaikki":
        filtered2_df = filtered_df
    else:
        filtered2_df = filtered_df[filtered_df["Kone"] == valittu_kone]

    filtered2_df = filtered2_df.copy()
    if valittu_ryhma == "Kaikki":
        kone_jarjestys = {nimi: idx for idx, nimi in enumerate(kaikki_koneet_jarjestyksessa)}
        filtered2_df["konejarjestys"] = filtered2_df["Kone"].map(lambda n: kone_jarjestys.get(n, 99999))
    else:
        kone_jarjestys = {nimi: idx for idx, nimi in enumerate(koneet_nimet)}
        filtered2_df["konejarjestys"] = filtered2_df["Kone"].map(lambda n: kone_jarjestys.get(n, 99999))
    filtered2_df["pvmjarjestys"] = pd.to_datetime(filtered2_df["Päivämäärä"], format="%d.%m.%Y", errors="coerce")
    filtered2_df = filtered2_df.sort_values(["konejarjestys", "pvmjarjestys"])

    df_naytto, index_map = konekohtainen_naytto_nimi_id_samalle_riville(filtered2_df, huolto_kohteet)
    df_naytto = df_naytto.reindex(columns=esikatselu_sarakkeet)
    df_naytto = df_naytto.fillna("--")
    if "Vapaa teksti" in df_naytto.columns:
        df_naytto["Vapaa teksti"] = df_naytto["Vapaa teksti"].replace("--", "")
        df_naytto["Vapaa teksti"] = df_naytto["Vapaa teksti"].replace("nan", "")
    for col in df_naytto.columns:
        df_naytto[col] = df_naytto[col].astype(str)

    st.dataframe(df_naytto)

    st.markdown("#### Lataa huoltohistoria PDF-tiedostona")
    if st.button("Lataa PDF"):
        pdf_naytto = df_naytto.drop(columns=["Rivi"]).copy()

        def pdf_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(420, 20, f"Sivu {doc.page}")
            canvas.restoreState()

        otsikkotyyli = ParagraphStyle(
            name='OtsikkoIso',
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=22,
            alignment=0
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

        kone_bold = ParagraphStyle("BoldKone", fontName="Helvetica-Bold", fontSize=8, alignment=0)
        normal_style = ParagraphStyle("Normaali", fontName="Helvetica", fontSize=8, alignment=0)

        data = [list(pdf_naytto.columns)]
        green_cells = []
        for i, (_, row) in enumerate(pdf_naytto.iterrows(), start=1):
            pdf_row = []
            for j, col in enumerate(pdf_naytto.columns):
                value = row[col]
                if col == "Kone" and value and not value.isdigit() and not value.strip().isdigit():
                    pdf_row.append(Paragraph(str(value), kone_bold))
                elif str(value).strip().lower() in ["ok", "✅", "✓"]:
                    pdf_row.append("\u2713")
                    green_cells.append((j, len(data)))
                else:
                    pdf_row.append(str(value))
            data.append(pdf_row)

        pdf_col_widths = [110, 80, 60, 80, 140] + [30] * (len(pdf_naytto.columns) - 5)
        table = Table(data, colWidths=pdf_col_widths, repeatRows=1)
        ts = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#51c987")),
            ('ALIGN',(0,0),(-1,-1),'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 8)
        ])
        for i in range(1, len(data)):
            if i % 2 == 1:
                ts.add('BACKGROUND', (0,i), (-1,i), colors.whitesmoke)
        for (j,i) in green_cells:
            ts.add('TEXTCOLOR', (j,i), (j,i), colors.green)
        table.setStyle(ts)
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            topMargin=35, leftMargin=40, rightMargin=40, bottomMargin=35
        )
        elements = [
            Spacer(1, 4*mm),
            otsikko_paivays_table,
            Spacer(1, 4*mm),
            table
        ]
        doc.build(elements, onFirstPage=pdf_footer, onLaterPages=pdf_footer)
        buffer.seek(0)
        st.download_button(
            label="Lataa PDF-tiedosto",
            data=buffer,
            file_name="huoltohistoria.pdf",
            mime="application/pdf"
        )

with tab3:
    st.header("Koneiden ja ryhmien hallinta")

    koneet_nyt = lue_koneet()
    ryhmat_lista = list(koneet_nyt.keys())

    st.subheader("Lisää kone")
    uusi_ryhma = st.selectbox("Ryhmän valinta tai luonti", ryhmat_lista+["Uusi ryhmä"], key="uusi_ryhma")
    kaytettava_ryhma = st.text_input("Uuden ryhmän nimi") if uusi_ryhma=="Uusi ryhmä" else uusi_ryhma
    uusi_nimi = st.text_input("Koneen nimi")
    uusi_id = st.text_input("Koneen ID-numero")
    if st.button("Lisää kone"):
        if kaytettava_ryhma and uusi_nimi and uusi_id:
            koneet_nyt.setdefault(kaytettava_ryhma, [])
            koneet_nyt[kaytettava_ryhma].append({"nimi": uusi_nimi, "id": uusi_id})
            tallenna_koneet(koneet_nyt)
            st.success(f"Kone {uusi_nimi} lisätty ryhmään {kaytettava_ryhma}")
            st.rerun()
        else:
            st.warning("Täytä kaikki kentät.")

    st.subheader("Poista kone")
    if ryhmat_lista:
        valitse_ryhma_poisto = st.selectbox("Valitse ryhmä (poistoa varten)", ryhmat_lista, key="poistoryhma")
        koneet_poisto = koneet_nyt.get(valitse_ryhma_poisto, [])
        if koneet_poisto:
            valitse_kone_poisto = st.selectbox("Valitse kone", [k["nimi"] for k in koneet_poisto], key="poistokone")
            if st.button("Poista kone"):
                koneet_nyt[valitse_ryhma_poisto] = [k for k in koneet_poisto if k["nimi"] != valitse_kone_poisto]
                if not koneet_nyt[valitse_ryhma_poisto]:
                    del koneet_nyt[valitse_ryhma_poisto]
                tallenna_koneet(koneet_nyt)
                st.success(f"Kone {valitse_kone_poisto} poistettu.")
                st.rerun()
        else:
            st.info("Valitussa ryhmässä ei koneita.")
    else:
        st.info("Ei ryhmiä.")

    st.markdown("---")
    st.subheader("Ryhmän koneet")
    if ryhmat_lista:
        ryhma_valinta = st.selectbox("Näytä koneet ryhmästä", ryhmat_lista, key="ryhmat_lista_nakyma")
        koneet_listattavaan = koneet_nyt.get(ryhma_valinta, [])
        if koneet_listattavaan:
            koneet_df = pd.DataFrame(koneet_listattavaan).rename(columns={"nimi": "Koneen nimi", "id": "ID"})
            st.table(koneet_df)
        else:
            st.info("Ryhmässä ei koneita.")
    else:
        st.info("Ei ryhmiä.")
