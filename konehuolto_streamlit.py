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
