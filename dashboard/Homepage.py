import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="Les Etablissements de centre de vieillesse en France",
    page_icon="🏘️",
    layout="wide"
)

# Appliquer un thème de couleurs discrètes
st.markdown("""
    <style>
        body {
            background-color: #f5f5f5;  /* Gris clair pour le fond */
            color: #3c3c3c;  /* Couleur de texte sombre */
        }
        .stButton>button {
            background-color: #85C1AE;  /* Vert doux */
            color: white;
            border-radius: 5px;
        }
        .stSidebar {
            background-color: #fafafa;  /* Fond clair pour la sidebar */
        }
        .stTitle {
            color: #3c3c3c;  /* Titre sombre pour contraster */
        }
    </style>
    """, unsafe_allow_html=True)

# Titre principal
st.title("Le Petit Monde de Léon")
st.markdown(
    """
    Bienvenue sur le tableau de bord interactif des EHPAD et autres établissements de soins en France. 
    Ce tableau de bord vous permet d'explorer les données sur les établissements, 
    y compris leur capacité, leur localisation et les tarifs appliqués.
    """
)   

st.image("./images/logo-leon.png")