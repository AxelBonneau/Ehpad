import streamlit as st
import pandas as pd
import os

# Configuration de la page, doit être la première commande Streamlit
st.set_page_config(
    page_title="Sièges sociales et dirigeants",
    page_icon="📈",
    layout="wide"  # Facultatif : change la mise en page par défaut
)

# Charger les données JSON dans un DataFrame
file_path = "./data/EHPAD.json"
df = pd.read_json(file_path)

# Normalisation de la structure JSON (si nécessaire)
# Si vos données JSON ont des colonnes imbriquées, utilisez json_normalize pour les aplatir.
df = pd.json_normalize(df.to_dict(orient='records'))

entreprise = df[["Nom_de_l'entreprise"]].drop_duplicates()

# Afficher ou utiliser dans Streamlit
st.write(entreprise)

# Champ de texte pour rechercher dans les départements
search_query = st.sidebar.text_input("Rechercher une entreprise", "")

# Filtrer les départements en fonction de la recherche
filtered_entreprise = [ent for ent in entreprise["Nom_de_l'entreprise"] if search_query.lower() in ent.lower()]

# Limiter à 10 résultats
filtered_entreprise = filtered_entreprise[:10]

# Afficher les entreprises filtrées en tant que boutons cliquables
if filtered_entreprise:
    st.sidebar.write("Résultats de la recherche :")
    for ent in filtered_entreprise:
        if st.sidebar.button(ent):
            # Afficher les informations complètes de l'entreprise sélectionnée
            selected_entreprise = df[df["Nom_de_l'entreprise"]==ent]

            # Renommer uniquement certaines colonnes tout en conservant les autres intactes
            selected_entreprise_renamed = selected_entreprise.copy()  # Crée une copie pour ne pas modifier l'original
            selected_entreprise_renamed["Nom_entreprise"] = selected_entreprise_renamed.pop("Nom_de_l'entreprise")
            selected_entreprise_renamed["CA"] = selected_entreprise_renamed.pop("Chiffre_d'affaires_kEUR")

            # Affichage des détails avec un design plus esthétique
            st.title(f"Détails de l'entreprise: {selected_entreprise_renamed.get('Nom_entreprise')}")

            # Informations générales sur l'entreprise
            st.subheader("Informations Générales")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**Adresse:** {selected_entreprise_renamed.get('Adresse', 'Non spécifié')}")
                st.markdown(f"**Ville:** {selected_entreprise_renamed.get('Ville', 'Non spécifié')}")
                st.markdown(f"**Code Postal:** {selected_entreprise_renamed.get('Code_postal', 'Non spécifié')}")
                st.markdown(f"**Numéro de téléphone:** {selected_entreprise_renamed.get('Téléphone', 'Non spécifié')}")
                
            with col2:
                st.markdown(f"**Date de création:** {selected_entreprise_renamed.get('Date_de_création', 'Non spécifié')}")
                st.markdown(f"**Effectif moyen:** {selected_entreprise_renamed.get('Effectif_moyen', 'Non spécifié')}")
                st.markdown(f"**Chiffre d'affaires (kEUR):** {selected_entreprise_renamed.get('CA', 'Non spécifié')}")
                st.markdown(f"**Fonds propres (kEUR):** {selected_entreprise_renamed.get('Fonds_propres_kEUR', 'Non spécifié')}")

            # Afficher les dirigeants si disponibles
            st.subheader("Dirigeants")
            dirigeants = selected_entreprise_renamed.get('Dirigeants', [])
            if not dirigeants.empty:
                st.write("Voici la liste des dirigeants de l'entreprise :")
                for dirigeant in dirigeants:
                    st.write(f"- {dirigeant}")
            else:
                st.write("Aucun dirigeant spécifié.")

            # Optionnel : ajouter un peu de style avec des bordures ou autres éléments visuels
            st.markdown("---")
