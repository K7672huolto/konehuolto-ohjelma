with tab1:
    st.header("Lisää uusi huoltotapahtuma")
    ryhmat_lista = sorted(list(koneet_data.keys()))
    if not ryhmat_lista:
        st.info("Ei yhtään koneryhmää vielä. Lisää koneita välilehdellä 'Koneet ja ryhmät'.")
    else:
        valittu_ryhma = st.selectbox("Ryhmä", ryhmat_lista, key="ryhma_selectbox")
        koneet_ryhmaan = koneet_data.get(valittu_ryhma, [])

        if koneet_ryhmaan:
            koneet_df2 = pd.DataFrame(koneet_ryhmaan)
            st.write("DEBUG: koneet_df2.columns:", koneet_df2.columns.tolist())

            # Etsi koneen nimen ja id:n oikea sarake-otsikko
            if "Kone" in koneet_df2.columns:
                kone_sarake = "Kone"
            elif "nimi" in koneet_df2.columns:
                kone_sarake = "nimi"
            else:
                st.error("Sheetissä ei saraketta 'Kone' tai 'nimi'. Nykyiset sarakkeet: " + str(list(koneet_df2.columns)))
                st.stop()

            if "ID" in koneet_df2.columns:
                id_sarake = "ID"
            elif "id" in koneet_df2.columns:
                id_sarake = "id"
            else:
                st.error("Sheetissä ei saraketta 'ID' tai 'id'. Nykyiset sarakkeet: " + str(list(koneet_df2.columns)))
                st.stop()

            koneet_df2[kone_sarake] = koneet_df2[kone_sarake].fillna("Tuntematon kone")
            kone_valinta = st.radio(
                "Valitse kone:",
                koneet_df2[kone_sarake].tolist(),
                key="konevalinta_radio",
                index=0 if len(koneet_df2) > 0 else None
            )
            kone_id = koneet_df2[koneet_df2[kone_sarake] == kone_valinta][id_sarake].values
            kone_id = kone_id[0] if len(kone_id) > 0 else ""
        else:
            st.info("Valitussa ryhmässä ei ole koneita.")
            kone_id = ""
            kone_valinta = ""

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
                if not valittu_ryhma or not kone_valinta or not kayttotunnit or not kone_id:
                    st.warning("Täytä ryhmä, kone, tunnit ja päivämäärä!")
                else:
                    uusi = {
                        "ID": str(uuid.uuid4())[:8],
                        "Kone": kone_valinta,
                        "ID-numero": kone_id,
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
