# ----------- TAB 4: KÄYTTÖTUNNIT -----------
with tab4:
    st.header("Kaikkien koneiden käyttötunnit ja erotus")
    if koneet_df.empty:
        st.info("Ei koneita lisättynä.")
    else:
        # --- Hae viimeisimmät huollot jokaiselle koneelle ---
        lista = []
        for kone in koneet_df["Kone"].tolist():
            ryhma = koneet_df.loc[koneet_df["Kone"] == kone, "Ryhmä"].values[0]
            kone_id = koneet_df.loc[koneet_df["Kone"] == kone, "ID"].values[0]

            huollot_koneelle = huolto_df[huolto_df["Kone"] == kone].copy()
            huollot_koneelle["Pvm_dt"] = pd.to_datetime(
                huollot_koneelle["Päivämäärä"], dayfirst=True, errors="coerce"
            )
            huollot_koneelle = huollot_koneelle.sort_values("Pvm_dt", ascending=False)

            if not huollot_koneelle.empty:
                viimeisin_huolto = huollot_koneelle.iloc[0]
                viimeiset_tunnit = int(float(str(viimeisin_huolto.get("Tunnit", 0)).replace(",", ".") or 0))
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
                "Syötä uudet tunnit": viimeiset_tunnit
            })

        df_init = pd.DataFrame(lista)

        # --- Session state taulukko (säilyttää muutokset) ---
        if "df_tunnit" not in st.session_state:
            st.session_state.df_tunnit = df_init.copy()

        df_tunnit = st.session_state.df_tunnit

        # --- Käyttöliittymä: + ja - napit ---
        for idx, row in df_tunnit.iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            col1.markdown(f"**{row['Kone']} ({row['Ryhmä']})**  — Viimeisin huolto: {row['Viimeisin huolto (pvm)']} ({row['Viimeisin huolto (tunnit)']} h)")
            new_val = col2.number_input(
                "Uudet tunnit", 
                min_value=0, step=1,
                value=int(row["Syötä uudet tunnit"]),
                key=f"input_{idx}"
            )
            if col3.button("+", key=f"plus_{idx}"):
                new_val += 1
            if col4.button("-", key=f"minus_{idx}"):
                new_val = max(0, new_val - 1)

            st.session_state.df_tunnit.at[idx, "Syötä uudet tunnit"] = new_val

        # --- Laske erotus ---
        df_tunnit["Erotus"] = df_tunnit["Syötä uudet tunnit"] - df_tunnit["Viimeisin huolto (tunnit)"]

        # --- Näytä esikatselu (st.dataframe ei tue värejä → käytetään st.data_editor) ---
        def style_row(row):
            color = "red" if row["Erotus"] != 0 else "black"
            return [
                f"font-weight: bold" if col in ["Kone", "ID"] else
                f"color:{color}" if col == "Erotus" else ""
                for col in row.index
            ]

        st.dataframe(df_tunnit.style.apply(style_row, axis=1), hide_index=True)

        # --- PDF-lataus ---
        from io import BytesIO
        def create_tab4_pdf(df):
            buffer = BytesIO()
            otsikkotyyli = ParagraphStyle(name="otsikko", fontName="Helvetica-Bold", fontSize=16)
            paivays = Paragraph(datetime.today().strftime("%d.%m.%Y"), ParagraphStyle("date", fontSize=12, alignment=2))
            otsikko = Paragraph("Kaikkien koneiden käyttötunnit ja erotus", otsikkotyyli)

            columns = ["Kone", "Ryhmä", "Viimeisin huolto (pvm)", 
                       "Viimeisin huolto (tunnit)", "Syötä uudet tunnit", "Erotus"]
            data = [columns]
            for _, r in df.iterrows():
                row = [
                    Paragraph(f"<b>{r['Kone']}</b>", ParagraphStyle("kone", fontSize=9)),
                    str(r["Ryhmä"]),
                    str(r["Viimeisin huolto (pvm)"]),
                    str(r["Viimeisin huolto (tunnit)"]),
                    str(r["Syötä uudet tunnit"]),
                    Paragraph(f"<font color='red'>{r['Erotus']}</font>", ParagraphStyle("ero", fontSize=9))
                ]
                data.append(row)

            table = Table(data, repeatRows=1, colWidths=[120, 100, 120, 120, 100, 60])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.teal),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))

            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
            doc.build([Spacer(1, 4*mm),
                       Table([[otsikko, paivays]], colWidths=[340, 340]),
                       Spacer(1, 4*mm),
                       table])
            buffer.seek(0)
            return buffer

        pdf_buffer = create_tab4_pdf(df_tunnit)
        st.download_button("📥 Lataa PDF", data=pdf_buffer, file_name="kaikkien_koneiden_tunnit.pdf", mime="application/pdf")

        # --- Tallenna kaikki yhdellä napilla ---
        if st.button("💾 Tallenna kaikki koneiden tunnit"):
            try:
                nyt = datetime.today().strftime("%d.%m.%Y %H:%M")
                out_df = df_tunnit.copy()
                out_df.insert(0, "Aika", nyt)
                tallenna_kayttotunnit_bulk(out_df[["Aika", "Kone", "Ryhmä", "Viimeisin huolto (tunnit)", "Syötä uudet tunnit", "Erotus"]])
                st.success("Kaikkien koneiden tunnit tallennettu Google Sheetiin!")
            except Exception as e:
                st.error(f"Tallennus epäonnistui: {e}")
