import streamlit as st
import pandas as pd
import json
import os
st.markdown("""
    <style>
    /* Poistaa ylämarginaalin ja tiivistää kaiken ylös */
    .block-container {
        padding-top: 0rem !important;
        margin-top: 0rem !important;
    }
    </style>
""", unsafe_allow_html=True)
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from PIL import Image
#from st_aggrid import AgGrid, GridOptionsBuilder

EXCEL_TIEDOSTO = "konehuollot.xlsx"
KONEET_TIEDOSTO = "koneet.json"

st.set_page_config(page_title="Konehuolto", layout="wide")

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


def konekohtainen_naytto_nimi_id_sitten_huollot_tyhjalla(df, huolto_kohteet):
    if df.empty:
        return pd.DataFrame([], columns=["Rivi"] + [c for c in df.columns if c != "ID"]), []
    df2 = df.copy()
    columns = ["Rivi"] + [c for c in df2.columns if c != "ID"]
    uudet_rivit = []
    index_map = []
    viime_kone = None
    koneen_huollot = []
    buffer_idxs = []
    rivinro = 1
    for idx, row in df2.iterrows():
        kone = row["Kone"]
        kone_id = str(row["ID"]) if "ID" in row else ""
        if kone != viime_kone:
            if viime_kone is not None:
                # Tyhjä rivi, jolla myös rivinumero (jätetään tyhjäksi)
                uudet_rivit.append({col: "" for col in columns})
                index_map.append(None)
                # Puretaan aiemmat huollot
                for i, h in enumerate(koneen_huollot):
                    r = {col: h[col] for col in columns if col != "Rivi"}
                    for kohta in huolto_kohteet:
                        val = str(h.get(kohta, "")).strip()
                        if val.lower() == "ok":
                            r[kohta] = "✅"
                        else:
                            r[kohta] = val
                    if i == 0:
                        r["Kone"] = viime_kone
                        r["Ryhmä"] = h["Ryhmä"]
                    elif i == 1:
                        r["Kone"] = viime_id
                        r["Ryhmä"] = ""
                    else:
                        r["Kone"] = ""
                        r["Ryhmä"] = ""
                    rivi = {"Rivi": rivinro}
                    rivi.update(r)
                    uudet_rivit.append(rivi)
                    rivinro += 1
                    if i > 1 or (i == 0 and viime_kone):
                        index_map.append(buffer_idxs[i])
                    else:
                        index_map.append(None)
                koneen_huollot = []
                buffer_idxs = []
            viime_kone = kone
            viime_id = kone_id
        koneen_huollot.append(row)
        buffer_idxs.append(idx)
    # Lopuksi viimeinen koneen bufferi
    if koneen_huollot:
        for i, h in enumerate(koneen_huollot):
            r = {col: h[col] for col in columns if col != "Rivi"}
            for kohta in huolto_kohteet:
                val = str(h.get(kohta, "")).strip()
                if val.lower() == "ok":
                    r[kohta] = "✅"
                else:
                    r[kohta] = val
            if i == 0:
                r["Kone"] = viime_kone
                r["Ryhmä"] = h["Ryhmä"]
            elif i == 1:
                r["Kone"] = viime_id
                r["Ryhmä"] = ""
            else:
                r["Kone"] = ""
                r["Ryhmä"] = ""
            rivi = {"Rivi": rivinro}
            rivi.update(r)
            uudet_rivit.append(rivi)
            rivinro += 1
            if i > 1 or (i == 0 and viime_kone):
                index_map.append(buffer_idxs[i])
            else:
                index_map.append(None)
    return pd.DataFrame(uudet_rivit, columns=columns), index_map




# Alustukset
alusta_koneet_json()
alusta_excel()
koneet = lue_koneet()
df = lue_data()

# (Valinnainen debug print jos haluat nähdä alussa rivimäärän)
#print("Alussa rivejä:", len(df))

import base64

def taustakuva_local(filename):
    with open(filename, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return f"data:image/jpg;base64,{encoded}"

kuva_base64 = taustakuva_local("tausta.png")

st.markdown(
    f"""
    <div style="
        background-image: url('{kuva_base64}');
        background-size: cover;
        background-position: center;
        padding: 80px 0 80px 0;
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
        # Nollaa kaikki kentät
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



#from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode

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

    # FUNKTIO: 2-malli
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
                # Täysin tyhjä väli!
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

    df_naytto, index_map = konekohtainen_naytto_nimi_id_samalle_riville(filtered2_df, huolto_kohteet)
    df_naytto = df_naytto.reindex(columns=esikatselu_sarakkeet)
    df_naytto = df_naytto.fillna("--")
    if "Vapaa teksti" in df_naytto.columns:
        df_naytto["Vapaa teksti"] = df_naytto["Vapaa teksti"].replace("--", "")
        df_naytto["Vapaa teksti"] = df_naytto["Vapaa teksti"].replace("nan", "")
    for col in df_naytto.columns:
        df_naytto[col] = df_naytto[col].astype(str)

    gb = GridOptionsBuilder.from_dataframe(df_naytto)
    gb.configure_default_column(editable=False, wrapText=True, autoHeight=True)
    gb.configure_column("Rivi", width=50)
    gb.configure_column("Kone", width=220)
    gb.configure_column("Ryhmä", width=120)
    gb.configure_column("Tunnit", width=80)
    gb.configure_column("Päivämäärä", width=110)
    gb.configure_column("Vapaa teksti", width=200)
    for kohde in huolto_kohteet:
        gb.configure_column(kohde, width=50)
    gb.configure_selection('single')
    grid_options = gb.build()

    fit = True

    grid_response = AgGrid(
        df_naytto,
        gridOptions=grid_options,
        fit_columns_on_grid_load=fit,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        theme="streamlit",
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        data_return_mode=DataReturnMode.FILTERED
    )

    selected_rows = grid_response['selected_rows']
    if selected_rows is not None and len(selected_rows) > 0:
        if hasattr(selected_rows, "iloc"):
            valittu_rivi = selected_rows.iloc[0].to_dict()
        else:
            valittu_rivi = selected_rows[0]
        naytto_idx = int(valittu_rivi['Rivi']) - 1
        # Tyhjää, koneen nimi tai ID-riviä ei voi muokata (index_mapissa None)
        if naytto_idx < len(index_map) and index_map[naytto_idx] is not None:
            data_idx = index_map[naytto_idx]
            row = filtered2_df.loc[data_idx]
            st.markdown("#### Muokkaa tai poista huoltotapahtuma")
            muokkaa = st.checkbox("Muokkaa tätä riviä", key=f"muokkaa_{naytto_idx}")
            if muokkaa:
                kayttotunnit_uusi = st.text_input("Tunnit/km", value=str(row["Tunnit"]), key=f"edit_tunnit_{naytto_idx}")
                pvm_uusi = st.text_input("Päivämäärä", value=str(row["Päivämäärä"]), key=f"edit_pvm_{naytto_idx}")
                vapaa_uusi = st.text_area("Vapaa teksti", value=str(row.get("Vapaa teksti", "")), key=f"edit_vapaa_{naytto_idx}")
                valinnat_uusi = {}
                for kohta in huolto_kohteet:
                    nykyarvo = str(row.get(kohta, "--"))
                    vaihtoehdot = ["--", "Vaihd", "Tark", "OK", "Muu"]
                    idx_vaihtoehto = vaihtoehdot.index(nykyarvo) if nykyarvo in vaihtoehdot else 0
                    valinnat_uusi[kohta] = st.selectbox(
                        f"{kohta}:", vaihtoehdot,
                        index=idx_vaihtoehto,
                        key=f"edit_{kohta}_{naytto_idx}"
                    )
                if st.button("Tallenna muutokset", key=f"tallenna_{naytto_idx}"):
                    idx = data_idx
                    for col in ["Vapaa teksti"] + huolto_kohteet:
                        if col in df.columns:
                            df[col] = df[col].astype(str)
                    df.at[idx, "Tunnit"] = str(kayttotunnit_uusi)
                    df.at[idx, "Päivämäärä"] = pvm_uusi
                    df.at[idx, "Vapaa teksti"] = vapaa_uusi
                    for kohta in huolto_kohteet:
                        if kohta in df.columns:
                            df.at[idx, kohta] = str(valinnat_uusi[kohta])
                    tallenna_data(df)
                    st.success("Muutokset tallennettu!")
                    st.rerun()
            if st.button("Poista tämä rivi", key=f"poista_{naytto_idx}"):
                idx = data_idx
                df = df.drop(idx)
                df = df.reset_index(drop=True)
                tallenna_data(df)
                st.success("Rivi poistettu!")
                st.rerun()
        else:
            st.info("Tyhjää väli-, koneen nimi- tai ID-riviä ei voi muokata.")
    else:
        st.info("Jos haluat muokata huoltoa klikkaa ensin muokattava rivi taulukosta.")




    st.markdown("#### Lataa huoltohistoria PDF-tiedostona")
    if st.button("Lataa PDF"):
        # Poista rivinumero ennen PDF:n muodostusta
        pdf_naytto = df_naytto.drop(columns=["Rivi"]).copy()

        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from datetime import datetime

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
        from io import BytesIO
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

    # --- Koneen lisäys ensimmäisenä ---
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

    # --- Koneen poisto heti seuraavana ---
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
    # --- Ryhmän koneet listataan tämän jälkeen ---
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
