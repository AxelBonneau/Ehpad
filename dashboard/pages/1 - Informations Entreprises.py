import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Aperçu des établissements français", page_icon="📈", layout = "wide")

# Charger les données JSON dans un DataFrame
file_path = "./data/base-etablissement.json"
df = pd.read_json(file_path)

# Normalisation de la structure JSON (si nécessaire)
# Si vos données JSON ont des colonnes imbriquées, utilisez json_normalize pour les aplatir.
df = pd.json_normalize(df.to_dict(orient='records'))

# Vérifier que les colonnes nécessaires sont présentes
required_columns = ["coordinates.deptname", "coordinates.deptcode", "capacity", "title", "noFinesset"]
if not all(col in df.columns for col in required_columns):
    raise ValueError("Le fichier JSON ne contient pas toutes les colonnes nécessaires : " + ", ".join(required_columns))

regions = df["coordinates.region"].dropna().unique().tolist()
departements = df["coordinates.deptname"].dropna().unique().tolist()
capacite = max(df["capacity"].dropna().unique().tolist())

# Sélection des filtres dans Streamlit
with st.sidebar.expander("Capacité d'accueil"):
    capacite_min = st.number_input("Capacité minimale d'accueil", min_value=0, value=0)
    capacite_max = st.number_input("Capacité maximale d'accueil", max_value=capacite, value=capacite)
    
# Liste des régions et des départements disponibles
regions = df["coordinates.region"].unique().tolist()
departements = df["coordinates.deptname"].unique().tolist()

# Obtenir les listes uniques pour les filtres
regions = df["coordinates.region"].unique().tolist()
departements = df["coordinates.deptname"].unique().tolist()
cities = df["coordinates.city"].unique().tolist()

# Initialiser les sélections
selected_region = None
selected_departement = None
selected_city = None

with st.sidebar.expander("Localisation"):
    # Sélection de la région
    selected_region = st.selectbox(
        "Choisissez une région", options=["(Toutes les régions)"] + regions
    )
    
    # Dynamique : départements filtrés par région
    if selected_region != "(Toutes les régions)":
        filtered_deps = (
            df[df["coordinates.region"] == selected_region]["coordinates.deptname"]
            .unique()
            .tolist()
        )
        selected_departement = st.selectbox(
            "Choisissez un département", options=["(Tous les départements)"] + filtered_deps
        )
    else:
        selected_departement = st.selectbox(
            "Choisissez un département", options=["(Tous les départements)"] + departements
        )

    # Dynamique : villes filtrées par département
    if selected_departement != "(Tous les départements)":
        filtered_cities = (
            df[df["coordinates.deptname"] == selected_departement]["coordinates.city"]
            .unique()
            .tolist()
        )
        selected_city = st.selectbox(
            "Choisissez une ville", options=["(Toutes les villes)"] + filtered_cities
        )
    elif selected_region != "(Toutes les régions)":
        # Si un département n'est pas choisi, filtrer par région pour la ville
        filtered_cities = (
            df[df["coordinates.region"] == selected_region]["coordinates.city"]
            .unique()
            .tolist()
        )
        selected_city = st.selectbox(
            "Choisissez une ville", options=["(Toutes les villes)"] + filtered_cities
        )
    else:
        selected_city = st.selectbox(
            "Choisissez une ville", options=["(Toutes les villes)"] + cities
        )

options_residence = ["EHPAD", "EHPA", "ESLD", "Résidence Autonomie", "Accueil de Jour"]
with st.sidebar.expander("Autres critères"):
    selection_residence = st.segmented_control("Type de Résidence : ", options_residence, selection_mode="multi", default=options_residence)

# Application des filtres sur le DataFrame
filtered_df = df.copy()
if selected_region != "(Toutes les régions)":
    filtered_df = filtered_df[filtered_df["coordinates.region"] == selected_region]
if selected_departement != "(Tous les départements)":
    filtered_df = filtered_df[filtered_df["coordinates.deptname"] == selected_departement]
if selected_city != "(Toutes les villes)":
    filtered_df = filtered_df[filtered_df["coordinates.city"] == selected_city]
filtered_df = filtered_df[(df.capacity >= capacite_min) & (df.capacity <= capacite_max)]

if "EHPAD" not in selection_residence:
    filtered_df = filtered_df[filtered_df["types.IsEHPAD"] == 0]
if "EHPA" not in selection_residence:
    filtered_df = filtered_df[filtered_df["types.IsEHPA"] == 0]
if "ESLD" not in selection_residence:
    filtered_df = filtered_df[filtered_df["types.IsESLD"] == 0]
if "Résidence Autonomie" not in selection_residence:
    filtered_df = filtered_df[filtered_df["types.IsRA"] == 0]
if "Accueil de Jour" not in selection_residence:
    filtered_df = filtered_df[filtered_df["types.IsAJA"] == 0] 

# Regrouper les données et calculer le nombre total de places par société
grouped_df = (filtered_df
    .groupby(["title", "noFinesset", "coordinates.region","coordinates.deptname", "coordinates.deptcode",
              "coordinates.city", "coordinates.latitude", "coordinates.longitude"], as_index=False)
    .agg({"capacity": "sum"})
    .rename(columns={
        "title": "Société", 
        "noFinesset": "noFinesset", 
        "coordinates.region": "region",
        "coordinates.deptname": "nom_departement", 
        "coordinates.deptcode": "no_departement", 
        "coordinates.city":"ville",
        "coordinates.latitude": "latitude", 
        "coordinates.longitude":"longitude",
        "capacity": "Nombre de Place"
    })
)

nbr_etablissement = grouped_df.shape[0]

st.header("Informations sur les Etablissement de vieillesse")
st.write(f"Nombre d'Etablissement trouvé : {nbr_etablissement}")

st.subheader("Tableau de données")
st.dataframe(grouped_df)

# Ajout d'un lien vers une icône (icône publique Mapbox, par exemple)
ICON_URL = "https://upload.wikimedia.org/wikipedia/commons/6/6b/Map_marker_icon_%E2%80%93_Nicolas_Mollet_%E2%80%93_Map_pointer_%E2%80%93_Desktop.png"
grouped_df["icon_data"] = grouped_df.apply(
    lambda row: {
        "url": ICON_URL,
        "width": 128,
        "height": 128,
        "anchorY": 128,  # Position de l'icône (128 correspond au bas de l'image)
    },
    axis=1
)

# Créer une carte Plotly
fig = px.scatter_mapbox(
    grouped_df,
    lat="latitude",
    lon="longitude",
    text="ville",  # Afficher le nom de la ville au survol
    zoom=5,
    height=500
)

# Définir le style Mapbox (utilise une clé API si nécessaire)
fig.update_layout(mapbox_style="carto-positron")

# Afficher la carte
st.plotly_chart(fig)
