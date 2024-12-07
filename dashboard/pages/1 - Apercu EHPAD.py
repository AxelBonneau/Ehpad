import streamlit as st
from pymongo import MongoClient
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from folium.plugins import MarkerCluster


st.set_page_config(page_title="Aperçu des établissements français", page_icon="📈")

client = MongoClient("mongodb+srv://axelbonneau:n2GyfDMtGb02M7n4@ehpad.rqwk5.mongodb.net/")
db = client["Ehpad"]
collection = db["base-emplacement"]

capacity_by_dept = pd.DataFrame(collection.aggregate(
    [
        {"$group": {
            "_id": "$coordinates.deptname",  # Regroupement par département
            "capacity": {"$sum": "$capacity"},  # Calcul de la capacité totale
            "latitude": {"$avg": "$coordinates.latitude"},  # Latitude (première occurrence)
            "longitude": {"$avg": "$coordinates.longitude"}  # Longitude (première occurrence)
        }},
        {"$project": {
            "Departement": "$_id",  # Renommage du champ "_id" en "Departement"
            "capacity": 1,  # Garder le champ "capacity"
            "_id": 0,  # Supprimer le champ "_id"
            "latitude": 1,
            "longitude": 1
        }}, 
        {"$sort" : {"capacity" : -1}}
    ]
))

# Affichage du tableau avec les informations
st.title("Tableau des Établissements de Vieillesse")
st.markdown("Voici un tableau avec les établissements de vieillesse en France, leur localisation et leur capacité.")
st.dataframe(capacity_by_dept)

# # Graphique interactif de la localisation des établissements
# st.subheader("Carte des Établissements")
# map_fig = px.scatter_mapbox(
#     data,
#     lat="coordinates.latitude",
#     lon="coordinates.longitude",
#     color="capacity",
#     size="capacity",
#     hover_name="title",
#     hover_data=["capacity", "coordinates.city", "coordinates.phone"],
#     zoom=5,
#     height=500
# )
# map_fig.update_layout(mapbox_style="open-street-map")
# st.plotly_chart(map_fig)

# # Box plot des tarifs (si les tarifs sont stockés dans un champ spécifique)
# st.subheader("Analyse des Tarifs des Établissements")
# tarifs_columns = ["ehpadPrice.prixHebPermCs", "ehpadPrice.tarifGir12", "ehpadPrice.tarifGir34"]
# tarifs_data = data[tarifs_columns].dropna()
# tarifs_fig = px.box(
#     tarifs_data,
#     points="all",
#     labels={"value": "Tarifs (en €)", "variable": "Type de Tarif"},
#     title="Distribution des Tarifs des Établissements"
# )
# st.plotly_chart(tarifs_fig)