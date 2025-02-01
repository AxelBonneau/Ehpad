import streamlit as st
import pandas as pd
import pydeck as pdk
import random
import numpy as np
import math
from sklearn.cluster import KMeans

st.set_page_config(page_title="Aperçu des établissements français", page_icon="📈", layout="wide")

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

df["Nom_Entreprise"] = df["title"] + " - " + df["noFinesset"]

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

# Application des filtres sur le DataFrame
filtered_df = df.copy()
if selected_region != "(Toutes les régions)":
    filtered_df = filtered_df[filtered_df["coordinates.region"] == (selected_region)]
if selected_departement != "(Tous les départements)":
    filtered_df = filtered_df[filtered_df["coordinates.deptname"] == (selected_departement)]
if selected_city != "(Toutes les villes)":
    filtered_df = filtered_df[filtered_df["coordinates.city"] == selected_city]
filtered_df = filtered_df[(df.capacity >= capacite_min) & (df.capacity <= capacite_max)]

groupe = filtered_df["Nom_Entreprise"].dropna().to_list()

options_residence = ["EHPAD", "EHPA", "ESLD", "Résidence Autonomie", "Accueil de Jour"]
with st.sidebar.expander("Autres critères"):    
    n_clusters = st.number_input(
        "Nombre de cluster : ", value=15, placeholder="Choisir un nombre..."
    )
    selection_residence = st.segmented_control("Type de Résidence : ", options_residence, selection_mode="multi", default=options_residence)


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
result_df = (filtered_df
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

def classify_region(lat, lon):
    if lon > -5 and lon < 10 and lat > 41 and lat < 51:  # France métropolitaine
        return "France Metropolitaine"
    else:
        return "Autre"

result_df["region_geographique"] = result_df.apply(lambda x: classify_region(x["latitude"], x["longitude"]), axis=1)

result_df = result_df.dropna(subset=['longitude', 'latitude'])

# Stockage des résultats
dfs = []

# Clustering par région
for region in result_df["region_geographique"].unique():
    # Filtrer les données pour chaque région
    region_df = result_df[result_df["region_geographique"] == region]
    coords = region_df[["longitude", "latitude"]].to_numpy()
    
    # Nombre de clusters basé sur le nombre de points dans la région
    n_clusters = min(n_clusters, len(coords))  # Par exemple, 5 clusters max ou moins si échantillons insuffisants

    if n_clusters > 1:  # Assurez-vous qu'il y a au moins 2 points pour KMeans
        coords = np.radians(coords)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        region_df["cluster"] = kmeans.fit_predict(coords)
    else:
        region_df["cluster"] = 0  # Assigne tous les points au même cluster si 1 seul échantillon
    
    dfs.append(region_df)

# Fonction pour convertir hex en RGB
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')  # Enlever le '#' du début
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]  # Convertir chaque paire de caractères en valeur RGB

df_final = pd.concat(dfs)

# Créez une palette pastel unique pour vos clusters
unique_clusters = df_final["cluster"].unique()
colors = {cluster: "#{:02x}{:02x}{:02x}".format(int(255 * random.uniform(0.4, 1)), 
                                                int(255 * random.uniform(0.4, 1)), 
                                               int(255 * random.uniform(0.4, 1))) 
          for cluster in unique_clusters}

# Assigner ces couleurs dans df_final
df_final["color"] = df_final["cluster"].map(colors)
df_final["rgb_color"] = df_final["color"].apply(hex_to_rgb)

df["exits_radius"] = df_final["Nombre de Place"].apply(lambda exits_count: math.exp(exits_count))

# Affichage de la carte avec pydeck
st.pydeck_chart(
    pdk.Deck(
        map_style="mapbox://styles/mapbox/dark-v10",  # Style sombre
        initial_view_state=pdk.ViewState(
            latitude=df_final["latitude"].mean(),
            longitude=df_final["longitude"].mean(),
            zoom=5,  # Zoom sur la carte, vous pouvez ajuster la valeur par défaut
            bearing=0,  # Rotation de la carte
            pitch=0,  # Inclinaison
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=df_final,
                get_position=["longitude", "latitude"],  # Coordonnées
                get_fill_color="rgb_color",  # Couleur basée sur le cluster
                radius_scale=100,  # Encore plus grand
                radius_min_pixels=4,  # Points bien visibles
                radius_max_pixels=300,  # Points qui peuvent devenir très gros en zoomant
                line_width_min_pixels=2,  # Bord plus épais pour bien les délimiter
                get_radius="exits_radius",  # Taille basée sur le nombre de places
                pickable=True,  # Interactions avec les points
                opacity=0.8,
                stroked=True,
                filled=True
            )
        ]
    )
)

# Ajouter une légende sous la carte
st.markdown("### Légende des Clusters")

# Afficher les clusters et leurs couleurs dynamiques
for cluster in sorted(df_final["cluster"].unique()):
    color = colors.get(cluster, "#000000")  # Couleur par défaut si non trouvée
    cluster_name = f"Cluster {cluster}" if cluster != -1 else "Bruit (Non classé)"
    st.markdown(
        f"<div style='display:flex; align-items:center; margin-bottom:5px;'>"
        f"<div style='width:20px; height:20px; background-color:{color}; margin-right:10px;'></div>"
        f"<div>{cluster_name}</div>"
        f"</div>",
        unsafe_allow_html=True
    )