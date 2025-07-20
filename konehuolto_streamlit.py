with tab3:
    st.header("Koneiden ja ryhmien hallinta")

    # --- Lisää kone ---
    st.subheader("Lisää kone")
    ryhmat_lista = list(koneet_df["Ryhmä"].dropna().unique())
    select_ryhmat = ryhmat_lista + ["Uusi ryhmä"]
    uusi_ryhma = st.selectbox(
        "Ryhmän valinta tai luonti",
        select_ryhmat,
        key="tab3_uusi_ryhma"
    )
    kaytettava_ryhma = st.text_input("Uuden ryhmän nimi", key="tab3_uusi_ryhman_nimi") if uusi_ryhma == "Uusi ryhmä" else uusi_ryhma
    uusi_nimi = st.text_input("Koneen nimi", key="tab3_koneen_nimi")
    uusi_id = st.text_input("Koneen ID-numero", key="tab3_koneen_id")

    if st.button("Lisää kone", key="lisaa_kone_nappi"):
        if kaytettava_ryhma and uusi_nimi and uusi_id:
            uusi = pd.DataFrame([{"Kone": uusi_nimi, "ID": uusi_id, "Ryhmä": kaytettava_ryhma}])
            uusi_koneet_df = pd.concat([koneet_df, uusi], ignore_index=True)
            tallenna_koneet(uusi_koneet_df)
            st.success(f"Kone {uusi_nimi} lisätty ryhmään {kaytettava_ryhma}")
            # --- Reset kentät ---
            st.session_state["tab3_uusi_ryhman_nimi"] = ""
            st.session_state["tab3_koneen_nimi"] = ""
            st.session_state["tab3_koneen_id"] = ""
            st.experimental_rerun()
        else:
            st.warning("Täytä kaikki kentät.")

    st.markdown("---")
    # --- Poista kone ---
    st.subheader("Poista kone")
    if not koneet_df.empty:
        poisto_ryhma = st.selectbox(
            "Valitse ryhmä (poistoa varten)",
            list(koneet_df["Ryhmä"].dropna().unique()),
            key="tab3_poisto_ryhma"
        )
        koneet_poisto = koneet_df[koneet_df["Ryhmä"] == poisto_ryhma]
        if not koneet_poisto.empty:
            poisto_nimi = st.selectbox("Valitse kone", koneet_poisto["Kone"].tolist(), key="tab3_poisto_kone")
            if st.button("Poista kone", key=f"poista_kone_{poisto_nimi}"):
                uusi_koneet_df = koneet_df[~((koneet_df["Ryhmä"] == poisto_ryhma) & (koneet_df["Kone"] == poisto_nimi))]
                tallenna_koneet(uusi_koneet_df)
                st.success(f"Kone {poisto_nimi} poistettu.")
                # --- Reset kentät ---
                st.session_state["tab3_uusi_ryhman_nimi"] = ""
                st.session_state["tab3_koneen_nimi"] = ""
                st.session_state["tab3_koneen_id"] = ""
                st.session_state["tab3_poisto_ryhma"] = ""
                st.session_state["tab3_poisto_kone"] = ""
                st.experimental_rerun()
        else:
            st.info("Valitussa ryhmässä ei koneita.")
    else:
        st.info("Ei ryhmiä.")

    st.markdown("---")
    # --- Ryhmän koneet ---
    st.subheader("Ryhmän koneet")
    if not koneet_df.empty:
        ryhma_valinta = st.selectbox(
            "Näytä koneet ryhmästä",
            list(koneet_df["Ryhmä"].dropna().unique()),
            key="tab3_ryhmat_lista_nakyma"
        )
        koneet_listattavaan = koneet_df[koneet_df["Ryhmä"] == ryhma_valinta]
        if not koneet_listattavaan.empty:
            koneet_df_nakyma = koneet_listattavaan[["Kone", "ID"]]
            st.table(koneet_df_nakyma)
        else:
            st.info("Ryhmässä ei koneita.")
    else:
        st.info("Ei ryhmiä.")
