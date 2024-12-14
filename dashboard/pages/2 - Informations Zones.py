import streamlit as st
import pandas as pd
import pydeck as pdk
from sklearn.cluster import KMeans


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
# Sélection multiple avec tous les départements sélectionnés par défaut
# CSS pour personnaliser l'apparence du widget
st.markdown("""
    <style>
    .stMultiSelect div[data-baseweb="select"] {
        background-color: #f0f4f8;
        border-radius: 5px;
        border: 1px solid #ccc;
        padding: 8px;
    }
    .stMultiSelect div[data-baseweb="select"] > div {
        max-height: 200px;  /* Limite la hauteur de la liste */
        overflow-y: auto;   /* Ajoute une barre de défilement verticale */
    }
    .stMultiSelect div[data-baseweb="select"] .dropdown-toggle {
        color: #4CAF50;  /* Change la couleur du texte du bouton */
    }
    </style>
""", unsafe_allow_html=True)

# Multiselect avec gestion de la taille et aspect esthétique
selected_departements = st.sidebar.multiselect(
    "Choisissez un ou plusieurs départements",  # Label
    options=departements,  # Liste des options
    key="selected_options", 
    default=departements,  # Par défaut, tout est sélectionné
    help="Sélectionnez un ou plusieurs départements pour afficher des informations.",
)


n_clusters = st.sidebar.number_input("Cluster", min_value=5, max_value=30, value=10)

# Filtrage des données selon les choix de l'utilisateur
filtered_df = df[
    (df["coordinates.deptname"].isin(selected_departements)) &  # Filtre les départements sélectionnés
    (df["capacity"] >= capacite_min)  # Filtre sur la capacité minimale
]

# Groupement et agrégation
grouped_df = (filtered_df
    .groupby(["title", "noFinesset", "coordinates.latitude", "coordinates.longitude"], as_index=False)
    .agg({"capacity": "sum"})  # Somme des capacités pour chaque groupe
    .rename(columns={
        "title": "Société",
        "noFinesset": "noFinesset",
        "coordinates.latitude": "latitude",
        "coordinates.longitude": "longitude",
        "capacity": "Nombre_de_Place"
    })
)

# Tri des résultats par le nombre de places en ordre décroissant
result_df = grouped_df.sort_values(by="Nombre_de_Place", ascending=False)

# Affichage dans Streamlit (ou utilisation ultérieure)
st.write(result_df)

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
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        region_df["cluster"] = kmeans.fit_predict(coords)
    else:
        region_df["cluster"] = 0  # Assigne tous les points au même cluster si 1 seul échantillon
    
    dfs.append(region_df)

df_final = pd.concat(dfs)

def generate_pastel_colors(n):
    import random
    colors = []
    for _ in range(n):
        # Générer des couleurs pastel distinctes
        r = int(255 * random.uniform(0.7, 1.0))
        g = int(255 * random.uniform(0.7, 1.0))
        b = int(255 * random.uniform(0.7, 1.0))
    
        
        # Ajouter la couleur RGBA à la liste
        colors.append([r, g, b])
    
    return colors

# Créez une palette pastel unique pour vos clusters
unique_clusters = df_final["cluster"].nunique()
pastel_colors = generate_pastel_colors(unique_clusters)

# Ajouter les couleurs pastel au DataFrame
df_final["color"] = df_final["cluster"].apply(lambda x: pastel_colors[x % len(pastel_colors)])


df_final["radius"] = df_final["Nombre_de_Place"] / df_final["Nombre_de_Place"].max() * 2000

# Fonction pour afficher les informations du point sélectionné
def display_selected_point(info):
    if info:
        st.write(f"Informations du point sélectionné : {info}")
    else:
        st.write("Aucun point sélectionné")

# Fonction pour calculer le rayon en fonction du zoom
def get_radius_scale(zoom_level):
    # Plus le zoom est élevé, plus l'échelle du rayon est petite
    return max(0.05, 10 / zoom_level)  # Ajuster la fonction pour obtenir l'effet souhaité


# Affichage avec pydeck
st.pydeck_chart(
    pdk.Deck(
        map_style="mapbox://styles/mapbox/dark-v10",  # Style sombre
        initial_view_state=pdk.ViewState(
            latitude=df_final["latitude"].mean(),
            longitude=df_final["longitude"].mean(),
            zoom=3,
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=df_final,
                get_position=["longitude", "latitude"],
                get_color="color",  # Couleurs pastel
                get_radius="radius",  # Appliquer un rayon basé sur le niveau de zoom
                radius_scale=get_radius_scale(3), 
                
                pickable=True,  # Permet d'interagir avec les éléments
                auto_highlight=True  # Met en surbrillance le point au survol
            )
        ],
        # Interaction sur clic
        tooltip={"html": "{Nombre_de_Place}", "style": {"color": "white"}},  # Afficher l'info du point
    )
)