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

st.header("Informations sur les Etablissements de vieillesse")
st.write(f"Nombre d'Etablissement trouvé : {nbr_etablissement}")

st.subheader("Carte des établissements d'EHPAD")
# Créer une carte Plotly
fig = px.scatter_mapbox(
    grouped_df,
    lat="latitude",
    lon="longitude",
    text="Société",  # Afficher le nom de la ville au survol
    zoom=5,
    height=500
)

fig.update_layout(mapbox_style="carto-positron")

event = st.plotly_chart(fig, on_select="rerun", selection_mode=["points"])

selected_points = event["selection"]["points"]

points_df = pd.DataFrame(selected_points)

if not points_df.empty:
    informations_point = pd.merge(points_df, 
                                  filtered_df, 
                                  left_on=["text", "lon", "lat"],
                                  right_on=["title", "coordinates.longitude", "coordinates.latitude"])
    
    informations_point = informations_point[[
        # 1. Informations générales sur l'établissement
        "_id", "title", "noFinesset", "capacity", "legal_status",
        
        # 2. Types d'établissements (booléens)
        "IsEHPAD", "IsEHPA", "IsESLD", "IsRA", "IsAJA", "IsHCOMPL", 
        "IsHTEMPO", "IsACC_JOUR", "IsACC_NUIT", "IsHAB_AIDE_SOC", 
        "IsCONV_APL", "IsALZH", "IsUHR", "IsPASA", "IsPUV", "IsF1", 
        "IsF1Bis", "IsF2",
        
        # 4. Coordonnées et localisation
        "coordinates.street", 
        "coordinates.postcode", "coordinates.deptcode", "coordinates.deptname", 
        "coordinates.city", "coordinates.phone", "coordinates.emailContact", 
        "coordinates.gestionnaire", "coordinates.website", 
        "coordinates.latitude", "coordinates.longitude", "coordinates.region"
    ]]

    # Mise en forme avec colonnes
    col1, col2 = st.columns(2)

    # Partie 1: Informations générales
    with col1:
        st.subheader("Informations générales")
        st.write(f"**Nom Etablissement**: {informations_point['title'][0]}")
        st.write(f"**Numéro FINESS**: {informations_point['noFinesset'][0]}")
        st.write(f"**Capacité**: {informations_point['capacity'][0]}")
        st.write(f"**Statut juridique**: {informations_point['legal_status'][0]}")

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
                st.checkbox(label=col, value=informations_point[col][0], disabled=True)
        
        with col2bis2:
            types_bool_cols2 = [ "IsHAB_AIDE_SOC", 
                "IsCONV_APL", "IsALZH", "IsUHR", "IsPASA", "IsPUV", "IsF1", 
                "IsF1Bis", "IsF2"
            ]
            for col in types_bool_cols2:
                st.checkbox(label=col, value=informations_point[col][0], disabled=True)


    # Partie 3: Coordonnées et localisation
    
    st.subheader("Coordonnées")
    col3, col4 = st.columns(2)
    with col3:
        st.write(f"**Rue**: {informations_point['coordinates.street'][0]}")
        st.write(f"**Ville**: {informations_point['coordinates.city'][0]}")
        st.write(f"**Code postal**: {informations_point['coordinates.postcode'][0]}")
        st.write(f"**Département**: {informations_point['coordinates.deptname'][0]}")
        st.write(f"**Région**: {informations_point['coordinates.region'][0]}")

    with col4:
        st.write(f"**Téléphone**: {informations_point['coordinates.phone'][0]}")
        st.write(f"**Email**: {informations_point['coordinates.emailContact'][0]}")
        st.write(f"**Gestionnaire**: {informations_point['coordinates.gestionnaire'][0]}")
        st.write(f"**Site Web**: {informations_point['coordinates.website'][0]}")
