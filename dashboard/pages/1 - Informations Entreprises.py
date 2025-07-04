import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(page_title="Aperçu des établissements français", page_icon="📈", layout="wide")

# Charger les données JSON dans un DataFrame
df = pd.read_csv("./data/dataset_to_use.csv", encoding="utf-8")

# Liste des régions, départements et villes
regions = df["coordinates.region"].dropna().unique().tolist()
departements = df["coordinates.deptname"].dropna().unique().tolist()
cities = df["coordinates.city"].dropna().unique().tolist()
df["Nom_Entreprise"] = df["title"] + " - " + df["noFinesset"]

# Capacité maximale
capacite = df["capacity"].dropna().max()

# Sélection des filtres dans Streamlit
with st.sidebar.expander("Capacité d'accueil"):
    capacite_min = st.number_input("Capacité minimale d'accueil", min_value=0, value=0)
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
    selection_residence = st.segmented_control("Type de Résidence : ", options_residence, selection_mode="multi", default=options_residence)


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
# Dans la section "Options de la carte"
with st.sidebar.expander("Options de la carte"):
    map_style = st.selectbox(
        "Style de carte",
        ["open-street-map", "carto-positron", "carto-darkmatter", "stamen-terrain", "stamen-toner", "stamen-watercolor"],
        index=0,
        help="Choisissez le style de la carte pour une meilleure visualisation"
    )
    # Option pour regrouper les points proches
    cluster_points = st.checkbox("Regrouper les points proches", value=False, help="Regroupe les points proches pour une meilleure lisibilité de la carte")
    # Option pour afficher la capacité proportionnelle
    show_capacity = st.checkbox("Taille proportionnelle à la capacité", value=True, help="Affiche la taille des points proportionnelle à la capacité d'accueil des établissements")
    
    # Nouvelle option pour le zoom
    zoom_sensitivity = st.slider(
        "Sensibilité du zoom", 
        min_value=1, 
        max_value=10, 
        value=8,
        help="Ajuste la sensibilité du zoom à la molette de la souris"
    )

# Créer une carte Plotly améliorée avec contrôle de zoom optimisé
if not map_df.empty:
    # Calcul du zoom initial basé sur l'étendue géographique
    if selected_city != "(Toutes les villes)":
        zoom_level = 11  # Zoom plus serré pour une ville
    elif selected_departement != "(Tous les départements)":
        zoom_level = 8   # Zoom moyen pour un département
    else:
        zoom_level = 5   # Vue large pour une région ou la France entière
        
    fig = px.scatter_mapbox(
        map_df,
        lat="coordinates.latitude",
        lon="coordinates.longitude",
        hover_name="Ville",
        hover_data={
            "Société": True,
            "Département": True,
            "Région": True,
            "Capacité": True,
            "coordinates.latitude": False,
            "coordinates.longitude": False
        },
        size="Capacité" if show_capacity else None,
        size_max=13 if show_capacity else 4,
        color_discrete_sequence=["#2a6c46"],
        height=600
    )
    
    # Personnaliser l'infobulle
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>" +
                     "Établissement: %{customdata[0]}<br>" +
                     "Département: %{customdata[1]}<br>" +
                     "Région: %{customdata[2]}<br>" +
                     "Capacité: %{customdata[3]} lits"
    )

    # Activer le clustering
    if cluster_points:
        fig.update_traces(cluster=dict(enabled=True, size=10))
    
    # Calcul du centre de la carte
    if not map_df.empty:
        center_lat = map_df["coordinates.latitude"].mean()
        center_lon = map_df["coordinates.longitude"].mean()
    else:
        center_lat, center_lon = 46.6031, 1.8883  # Centre de la France par défaut
    
    # Mise en forme de la carte avec paramètres de zoom optimisés
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
            # Paramètres pour un contrôle de zoom plus sensible
            bearing=0,
            pitch=0,
            accesstoken=None,
            uirevision=True
        ),
        # Configuration avancée du zoom
        autosize=True,
        clickmode='event+select'
    )
    
    # Ajouter des contrôles de navigation plus visibles
    fig.update_layout(
        mapbox_zoom=zoom_level,
        mapbox_center={"lat": center_lat, "lon": center_lon},
        mapbox_accesstoken=None
    )
    
    # Remplacer la configuration existante par :
    config = {
        'scrollZoom': True,
        'scrollZoomSpeed': 0.1 * zoom_sensitivity,  # Contrôle de la sensibilité
        'displayModeBar': True,
        'modeBarButtonsToAdd': ['zoomIn', 'zoomOut', 'resetView'],
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
        'displaylogo': False
    }
    
    st.plotly_chart(
        fig, 
        use_container_width=True, 
        config=config, 
        key="map_selector",
        on_select="rerun"
    )

else:
    st.warning("Aucun établissement trouvé avec les critères sélectionnés")

# Vérifier si une sélection existe dans l'état de session
if "map_selector" in st.session_state and "selection" in st.session_state["map_selector"]:
    if st.session_state.map_selector["selection"] and "points" in st.session_state.map_selector["selection"]:
        selected_points = st.session_state.map_selector["selection"]["points"]
        if selected_points:
            point = selected_points[0]
            
            # Filtrer les données pour trouver l'établissement correspondant
            mask = (
                (filtered_df["coordinates.latitude"] == point["lat"]) & 
                (filtered_df["coordinates.longitude"] == point["lon"])
            )
            informations_point = filtered_df[mask]
            
            if not informations_point.empty:
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