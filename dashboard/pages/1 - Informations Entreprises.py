import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from streamlit_plotly_events import plotly_events

st.set_page_config(page_title="Aperçu des établissements français", page_icon="📈", layout="wide")

# Charger les données
@st.cache_data
def load_data(path):
    df = pd.read_csv(path, encoding="utf-8")
    df["Nom_Entreprise"] = df["title"] + " - " + df["noFinesset"]
    return df

df = load_data("./data/dataset_to_use.csv")

# Liste des régions, départements et villes
regions = df["coordinates.region"].dropna().unique().tolist()
departements = df["coordinates.deptname"].dropna().unique().tolist()
cities = df["coordinates.city"].dropna().unique().tolist()
df["Nom_Entreprise"] = df["title"] + " - " + df["noFinesset"]

# Capacité maximale
capacite = df["capacity"].dropna().max()

# Sélection des filtres dans Streamlit
with st.sidebar.expander("Capacité d'accueil"):
    capacite_min = st.number_input("Capacité minimale d'accueil", min_value=0, value=70)
    capacite_max = st.number_input("Capacité maximale d'accueil", max_value=int(capacite), value=int(capacite))

# Initialiser les sélections
selected_region = None
selected_departement = None
selected_city = None

# Application des filtres sur le DataFrame
filtered_df = df.copy()
with st.sidebar.expander("Localisation"):
    # Sélection de la région
    selected_region = st.selectbox(
        "Choisissez une région", options=["(Toutes les régions)"] + regions
    )
    
    # Dynamique : départements filtrés par région
    if selected_region != "(Toutes les régions)":
        filtered_deps = (
            filtered_df[filtered_df["coordinates.region"] == selected_region]["coordinates.deptname"]
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
            filtered_df[filtered_df["coordinates.deptname"] == selected_departement]["coordinates.city"]
            .unique()
            .tolist()
        )
        selected_city = st.selectbox(
            "Choisissez une ville", options=["(Toutes les villes)"] + filtered_cities
        )
    elif selected_region != "(Toutes les régions)":
        # Si un département n'est pas choisi, filtrer par région pour la ville
        filtered_cities = (
            filtered_df[filtered_df["coordinates.region"] == selected_region]["coordinates.city"]
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


if selected_region != "(Toutes les régions)":
    filtered_df = filtered_df[filtered_df["coordinates.region"] == (selected_region)]
if selected_departement != "(Tous les départements)":
    filtered_df = filtered_df[filtered_df["coordinates.deptname"] == (selected_departement)]
if selected_city != "(Toutes les villes)":
    filtered_df = filtered_df[filtered_df["coordinates.city"] == selected_city]
filtered_df = filtered_df[(filtered_df.capacity >= capacite_min) & (filtered_df.capacity <= capacite_max)]

groupe = filtered_df["Nom_Entreprise"].dropna().to_list()

options_residence = ["EHPAD", "EHPA", "ESLD", "Résidence Autonomie", "Accueil de Jour"]
with st.sidebar.expander("Autres critères"):
    selection_groupe = st.selectbox("Nom du Groupe", options=["(Tous les groupes)"] + groupe, placeholder="Nom du groupe ou N°Finness")
    selection_residence = st.segmented_control("Type de Résidence : ", options_residence, selection_mode="multi", default=["EHPAD", "Résidence Autonomie"], help="Sélectionnez les types de résidence à afficher")


if "EHPAD" not in selection_residence:
    filtered_df = filtered_df[filtered_df["IsEHPAD"] == 0]
if "EHPA" not in selection_residence:
    filtered_df = filtered_df[filtered_df["IsEHPA"] == 0]
if "ESLD" not in selection_residence:
    filtered_df = filtered_df[filtered_df["IsESLD"] == 0]
if "Résidence Autonomie" not in selection_residence:
    filtered_df = filtered_df[filtered_df["IsRA"] == 0]
if "Accueil de Jour" not in selection_residence:
    filtered_df = filtered_df[filtered_df["IsAJA"] == 0] 

if selection_groupe != "(Tous les groupes)":
    filtered_df = filtered_df[filtered_df["Nom_Entreprise"] == selection_groupe]

# Préparer les données pour la carte
map_df = filtered_df.rename(columns={
    "title": "Société",
    "coordinates.city": "Ville",
    "coordinates.deptname": "Département",
    "coordinates.region": "Région",
    "capacity": "Capacité"
})

nbr_etablissement = map_df.shape[0]

st.header("Informations sur les Etablissements de vieillesse")

# Indicateurs clés en haut de page
col1, col2, col3 = st.columns(3)
col1.metric("📊 Nombre d'établissements", nbr_etablissement)
col2.metric("🧓 Capacité totale", f"{map_df['Capacité'].sum():,} lits")
col3.metric("📍 Région sélectionnée", selected_region if selected_region != "(Toutes les régions)" else "Toute la France")

st.subheader("Carte des établissements")

# Options de la carte
with st.sidebar.expander("Options de la carte"):
    map_style = st.selectbox(
        "Style de carte",
        ["open-street-map", "carto-positron", "carto-darkmatter", "stamen-terrain", "stamen-toner", "stamen-watercolor"],
        index=0,
        help="Choisissez le style de la carte pour une meilleure visualisation"
    )
    cluster_points = st.checkbox("Regrouper les points proches", value=False, help="Regroupe les points proches pour une meilleure lisibilité de la carte")
    show_capacity = st.checkbox("Taille proportionnelle à la capacité", value=True, help="Affiche la taille des points proportionnelle à la capacité d'accueil des établissements")
    
    zoom_sensitivity = st.slider(
        "Sensibilité du zoom", 
        min_value=1, 
        max_value=10, 
        value=8,
        help="Ajuste la sensibilité du zoom à la molette de la souris"
    )

# Initialiser l'état de session pour la sélection et la vue de la carte
if "selected_point" not in st.session_state:
    st.session_state.selected_point = None
if "map_view" not in st.session_state:
    st.session_state.map_view = {"zoom": None, "center": None}

# Gestion de la sélection de point
if "map_selector" in st.session_state and st.session_state.map_selector.get("selection", {}).get("points"):
    selected_point = st.session_state.map_selector["selection"]["points"][0]
    st.session_state.selected_point = {
        "lat": selected_point["lat"],
        "lon": selected_point["lon"]
    }

if not map_df.empty:
    # Calcul du zoom initial basé sur l'étendue géographique
    if selected_city != "(Toutes les villes)":
        default_zoom = 11
    elif selected_departement != "(Tous les départements)":
        default_zoom = 8
    else:
        default_zoom = 5
    
    # Utiliser la vue stockée ou la vue par défaut
    if st.session_state.map_view["zoom"] and st.session_state.map_view["center"]:
        zoom_level = st.session_state.map_view["zoom"]
        center_lat = st.session_state.map_view["center"]["lat"]
        center_lon = st.session_state.map_view["center"]["lon"]
    else:
        zoom_level = default_zoom
        center_lat = map_df["coordinates.latitude"].mean()
        center_lon = map_df["coordinates.longitude"].mean()
    
    # Si un point est sélectionné, zoomer dessus
    if st.session_state.selected_point:
        point = st.session_state.selected_point
        # Zoomer sur le point sélectionné
        zoom_level = 15
        center_lat = point["lat"]
        center_lon = point["lon"]
    
    # Ajouter une colonne de couleur (vert par défaut)
    map_df["color"] = "#741771"
    
    # Ajouter une colonne d'opacité
    map_df["opacity"] = 0.9  # Transparence légère par défaut
    
    # Si un point est sélectionné, le mettre en évidence
    if st.session_state.selected_point:
        point = st.session_state.selected_point
        # Trouver l'index du point sélectionné
        mask = (
            (map_df["coordinates.latitude"] == point["lat"]) & 
            (map_df["coordinates.longitude"] == point["lon"])
        )
        # Mettre le point sélectionné en bleu et complètement opaque
        map_df.loc[mask, "color"] = "#4182ad"
        map_df.loc[mask, "opacity"] = 1.0
    
    # Calcul dynamique de la taille basée sur le zoom
    base_size = 6 if show_capacity else 2
    
    # Ajuster la taille en fonction du zoom (plus le zoom est élevé, plus les points sont grands)
    dynamic_size = base_size * (1 + zoom_level / 15)
    
    # Définir la taille minimale et maximale
    min_size = 3  # Taille minimale absolue
    max_size = 15  # Taille maximale absolue
    
    # Appliquer les limites de taille
    dynamic_size = max(dynamic_size, min_size)  # Garantir une taille minimale
    dynamic_size = min(dynamic_size, max_size)  # Limiter la taille maximale
    
    # Préparer les données pour Plotly
    hover_data_config = {
        "Société": True,
        "Département": True,
        "Région": True,
        "Capacité": True,
        "coordinates.latitude": False,
        "coordinates.longitude": False,
        "color": False,
        "opacity": False
    }
    
    # Créer la figure en fonction du mode d'affichage de la capacité
    if show_capacity:
        fig = px.scatter_mapbox(
            map_df,
            lat="coordinates.latitude",
            lon="coordinates.longitude",
            hover_name="Ville",
            hover_data=hover_data_config,
            size="Capacité",
            size_max=dynamic_size,
            color="color",
            color_discrete_map="identity",
            opacity=map_df["opacity"],
            height=600
        )
    else:
        # Utiliser une taille fixe pour tous les points
        fig = px.scatter_mapbox(
            map_df,
            lat="coordinates.latitude",
            lon="coordinates.longitude",
            hover_name="Ville",
            hover_data=hover_data_config,
            size=[dynamic_size] * len(map_df),  # Taille constante pour tous les points
            color="color",
            color_discrete_map="identity",
            opacity=map_df["opacity"],
            height=600
        )
    
    # Personnaliser l'infobulle
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>" +
                     "Établissement: %{customdata[0]}<br>" +
                     "Département: %{customdata[1]}<br>" +
                     "Région: %{customdata[2]}<br>" +
                     "Capacité: %{customdata[3]} lits",
        marker=dict(
            sizemode='diameter',  # Mode de taille par diamètre
            sizemin=min_size       # Taille minimale garantie pour tous les points
        )
    )

    # Activer le clustering
    if cluster_points:
        fig.update_traces(
            cluster=dict(
                enabled=True,
                size=10,
                step=3,
                color='rgba(231, 76, 60, 0.5)',
                opacity=0.7,
            )
        )
    
    # Mise en forme de la carte
    fig.update_layout(
        mapbox_style=map_style,
        margin={"r":0,"t":0,"l":0,"b":0},
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
            font_family="Arial"
        ),
        mapbox=dict(
            center=dict(lat=center_lat, lon=center_lon),
            zoom=zoom_level,
            bearing=0,
            pitch=0,
            uirevision=True
        ),
        autosize=True,
        clickmode='event+select'
    )
    
    # Configuration du zoom
    config = {
        'scrollZoom': True,
        'scrollZoomSpeed': 0.1 * zoom_sensitivity,
        'displayModeBar': True,
        'modeBarButtonsToAdd': ['zoomIn', 'zoomOut', 'resetView'],
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
        'displaylogo': False
    }
    
    # Afficher la carte et gérer la sélection
    chart = st.plotly_chart(
        fig, 
        use_container_width=True, 
        config=config, 
        key="map_selector",
        on_select="rerun"
    )
    
    # Stocker l'état actuel de la vue (zoom et centre)
    st.session_state.map_view = {
        "zoom": zoom_level,
        "center": {"lat": center_lat, "lon": center_lon}
    }
    
    # Bouton pour effacer la sélection
    if st.session_state.selected_point and st.button("Effacer la sélection"):
        st.session_state.selected_point = None
        st.session_state.map_view = {"zoom": default_zoom, "center": None}
        st.rerun()

else:
    st.warning("Aucun établissement trouvé avec les critères sélectionnés")

# Gestion de la sélection d'un point
if "map_selector" in st.session_state and "selection" in st.session_state["map_selector"]:
    if st.session_state.map_selector["selection"] and "points" in st.session_state.map_selector["selection"]:
        selected_points = st.session_state.map_selector["selection"]["points"]
        if selected_points:
            # Stocker le point sélectionné dans l'état de session
            st.session_state.selected_point = selected_points[0]

# Afficher les détails du point sélectionné
if st.session_state.selected_point:
    point = st.session_state.selected_point
    
    # Filtrer les données pour trouver l'établissement correspondant
    mask = (
        (abs(filtered_df["coordinates.latitude"] - point["lat"]) < 0.0001) & 
        (abs(filtered_df["coordinates.longitude"] - point["lon"]) < 0.0001)
    )
    informations_point = filtered_df[mask]
    
    if not informations_point.empty:
        # Créer un expander pour les détails
        with st.expander(f"🔍 Détails de l'établissement: {informations_point['title'].values[0]}", expanded=True):
            # Mise en forme avec colonnes
            col1, col2 = st.columns(2)

            # Partie 1: Informations générales
            with col1:
                st.subheader("Informations générales")
                st.write(f"**Nom Etablissement**: {informations_point['title'].values[0]}")
                st.write(f"**Numéro FINESS**: {informations_point['noFinesset'].values[0]}")
                st.write(f"**Capacité**: {informations_point['capacity'].values[0]}")
                st.write(f"**Statut juridique**: {informations_point['legal_status'].values[0]}")

            # Partie 2: Types d'établissements
            with col2:
                st.subheader("Types d'établissements")
                col2bis1, col2bis2 = st.columns(2)

                with col2bis1:
                    types_bool_cols = [
                        "IsEHPAD", "IsEHPA", "IsESLD", "IsRA", "IsAJA", "IsHCOMPL", 
                        "IsHTEMPO", "IsACC_JOUR", "IsACC_NUIT"   
                    ]
                    for col in types_bool_cols:
                        st.checkbox(label=col, value=informations_point[col].values[0], disabled=True)
                
                with col2bis2:
                    types_bool_cols2 = [ 
                        "IsHAB_AIDE_SOC", "IsCONV_APL", "IsALZH", "IsUHR", 
                        "IsPASA", "IsPUV", "IsF1", "IsF1Bis", "IsF2"
                    ]
                    for col in types_bool_cols2:
                        st.checkbox(label=col, value=informations_point[col].values[0], disabled=True)

            # Partie 3: Coordonnées et localisation
            st.subheader("Coordonnées")
            col3, col4 = st.columns(2)
            with col3:
                st.write(f"**Rue**: {informations_point['coordinates.street'].values[0]}")
                st.write(f"**Ville**: {informations_point['coordinates.city'].values[0]}")
                st.write(f"**Code postal**: {informations_point['coordinates.postcode'].values[0]}")
                st.write(f"**Département**: {informations_point['coordinates.deptname'].values[0]}")
                st.write(f"**Région**: {informations_point['coordinates.region'].values[0]}")

            with col4:
                st.write(f"**Téléphone**: {informations_point['coordinates.phone'].values[0]}")
                st.write(f"**Email**: {informations_point['coordinates.emailContact'].values[0]}")
                st.write(f"**Gestionnaire**: {informations_point['coordinates.gestionnaire'].values[0]}")
                st.write(f"**Site Web**: {informations_point['coordinates.website'].values[0]}")