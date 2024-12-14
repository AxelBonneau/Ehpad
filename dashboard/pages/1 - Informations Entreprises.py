import streamlit as st
import pandas as pd

st.set_page_config(page_title="Aperçu des établissements français", page_icon="📈")

# Charger les données JSON dans un DataFrame
file_path = "./../Data/base-etablissement.json"
df = pd.read_json(file_path)

# Normalisation de la structure JSON (si nécessaire)
# Si vos données JSON ont des colonnes imbriquées, utilisez json_normalize pour les aplatir.
df = pd.json_normalize(df.to_dict(orient='records'))

# Vérifier que les colonnes nécessaires sont présentes
required_columns = ["coordinates.deptname", "coordinates.deptcode", "capacity", "title", "noFinesset"]
if not all(col in df.columns for col in required_columns):
    raise ValueError("Le fichier JSON ne contient pas toutes les colonnes nécessaires : " + ", ".join(required_columns))

# Sélection des filtres dans Streamlit
departements = df["coordinates.deptname"].dropna().unique().tolist()
capacite_min = st.sidebar.number_input("Capacité minimale d'accueil", min_value=0, value=0)
capacite_max = st.sidebar.number_input("Capacité maximale d'accueil", min_value=0, value=1000)
selected_departement = st.sidebar.selectbox("Choisissez un département", options=departements)

# Application des filtres sur le DataFrame
filtered_df = df[
    (df["coordinates.deptname"] == selected_departement) &
    (df["capacity"] >= capacite_min) &
    (df["capacity"] <= capacite_max)
]

# Regrouper les données et calculer le nombre total de places par société
grouped_df = (filtered_df
    .groupby(["title", "noFinesset", "coordinates.deptname", "coordinates.deptcode"], as_index=False)
    .agg({"capacity": "sum"})
    .rename(columns={
        "title": "Société", 
        "noFinesset": "noFinesset", 
        "coordinates.deptname": "nom_departement", 
        "coordinates.deptcode": "no_departement", 
        "capacity": "Nombre de Place"
    })
)

# Ajouter une colonne 'Afficher' pour afficher le nom de la société et la capacité d'accueil
grouped_df['Afficher'] = grouped_df['Société'] + " - Capacité: " + grouped_df['Nombre de Place'].astype(str)
grouped_df['departement'] = grouped_df['no_departement'] + ' - ' + grouped_df['nom_departement'].astype(str)


if not grouped_df.empty:
    # Affichage du tableau dans la sidebar
    st.sidebar.write("### Liste des sociétés")
    st.sidebar.table(grouped_df[['Société', 'Nombre de Place']])

    # Sélectionner une société
    selected_société = st.selectbox("Choisissez une société", grouped_df["Société"].tolist())

    # Recherche des détails pour la société sélectionnée
    if selected_société:
        société_details = filtered_df[filtered_df["title"] == selected_société]

        # Extraire les détails pertinents
        if not société_details.empty:
            # Extraction des informations
            titre = société_details.get("title")
            statut = société_details.get("legal_status")
            capacité = société_details.get("capacity")
            types = société_details.get("types", {})
            departement = société_details.get("coordinates", {}).get("deptname")
            adresse = société_details.get("coordinates", {}).get("street")
            ville = société_details.get("coordinates", {}).get("city")
            téléphone = société_details.get("coordinates", {}).get("phone")
            email = société_details.get("coordinates", {}).get("emailContact")
            gestionnaire = société_details.get("coordinates", {}).get("gestionnaire") 
            latitude = société_details.get("coordinates", {}).get("latitude")
            longitude = société_details.get("coordinates", {}).get("longitude")

            # Affichage des informations détaillées
            st.write(f"### Détails de la société : {titre}")
            st.write(f"**Statut Légal** : {statut}")
            st.write(f"**Capacité d'accueil** : {capacité}")
            st.write(f"**Type de structure** : {', '.join([k for k, v in types.items() if v])}")
            st.write(f"**Département** : {departement}")
            st.write(f"**Adresse** : {adresse}")
            st.write(f"**Ville** : {ville}")
            st.write(f"**Téléphone** : {téléphone}")
            st.write(f"**Email** : {email}")
            st.write(f"**Gestionnaire** : {gestionnaire}")
            st.write(f"**Latitude / Longitude** : ({latitude}, {longitude})")

        else:
            st.write("Détails non disponibles pour cette société.")
else:
    st.write("Aucune société ne correspond à votre recherche.")

