import streamlit as st
import pandas as pd
import json
import re
import datetime
import uuid

# Configurer la page
st.set_page_config(page_title="Gestion des Établissements", page_icon="📋", layout="wide")
st.title("Gestion des Établissements")

# Charger les métadonnées des colonnes
@st.cache_data
def load_metadata():
    metadata = pd.read_csv("./data/noms_colonnes.csv", sep=";")
    return metadata.set_index('Column Names')['Type Widget'], metadata.set_index('Column Names')['Modification Obligatoire']

widget_types, mandatory_fields = load_metadata()

# Charger les données JSON
@st.cache_resource
def load_data(file_path):
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        df = pd.json_normalize(data)
        # Convertir les champs Date
        date_cols = [col for col, wt in widget_types.items() if 'Date' in wt]
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement du fichier : {e}")
        return pd.DataFrame()

def save_data(dataframe, file_path):
    # Convertir les datetime.date en strings
    for col in dataframe.columns:
        if dataframe[col].dtype == 'datetime64[ns]':
            dataframe[col] = dataframe[col].dt.strftime('%Y-%m-%d')
    try:
        with open(file_path, "w") as f:
            json.dump(dataframe.to_dict(orient="records"), f, indent=4)
        st.success("Données sauvegardées avec succès !")
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde : {e}")
        
# Charger les données
df = load_data("./data/base-etablissement.json")

# Définir les options pour les selectbox
OPTIONS_CONFIG = {
    'legal_status': df["legal_status"].unique().tolist()
}

def get_unique_values(column_name):
    """Récupère les valeurs uniques d'une colonne dans la base de données."""
    if column_name in df.columns:
        unique_values = df[column_name].dropna().unique().tolist()
        return unique_values
    return []

# Fonction de validation
def validate_input(value, widget_type, mandatory):
    if mandatory and (value == "" or pd.isnull(value)):
        return False
    if widget_type == 'Structure telephonique':
        return re.match(r'^\+?[0-9 .-]{8,}$', str(value))
    if widget_type == 'Structure mail':
        return re.match(r'^[\w.-]+@[\w.-]+\.\w+$', str(value))
    return True

# Configuration des sections
SECTION_CONFIG = {
    "📌 Informations Générales": [
        '_id', 'title', 'noFinesset', 'capacity', 
        'legal_status', 'isViaTrajectoire', 'updatedAt'
    ],
    "🏷️ Types d'Établissement": [
        col for col in df.columns if col.startswith('types.')
    ],
    "📍 Coordonnées": [
        col for col in df.columns if col.startswith('coordinates.')
    ],
    "💰 Prix EHPAD": [
        col for col in df.columns if col.startswith('ehpadPrice.')
    ],
    "📊 Prix Résidence Autonomie": [
        col for col in df.columns if col.startswith('raPrice.')
    ]
}

# Style personnalisé
st.markdown("""
    <style>
    .stContainer {
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        background: #f9f9f9;
    }
    .section-title {
        font-size: 1.3em !important;
        color: #2c3e50 !important;
        border-bottom: 2px solid #3498db;
        padding-bottom: 5px;
        margin-bottom: 15px !important;
    }
    .required-field {
        color: #e74c3c;
        font-size: 0.9em;
    }
    .stButton>button {
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

def create_form_section(title, fields, entry, updates, key_prefix=""):
    """Crée une section de formulaire générique avec clés uniques"""
    with st.container():
        if title:
            st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
        cols = st.columns(2)
        col_index = 0
        
        for field in fields:
            widget_type = widget_types.get(field, 'Char 256')
            mandatory = mandatory_fields.get(field, 0)
            
            with cols[col_index]:
                field_name = field.split('.')[-1].replace('_', ' ').title()
                label = f"**{field_name}**"
                if mandatory:
                    label += " <span class='required-field'>*</span>"
                
                # Générer une clé unique pour chaque widget
                widget_key = f"{key_prefix}_{field}".replace(' ', '_').lower()

                if 'Selectbox' in widget_type:
                    options = OPTIONS_CONFIG.get(field, [])
                    current_value = entry.get(field, '')
                    index = options.index(current_value) if current_value in options else 0
                    updates[field] = st.selectbox(label, options=options, index=index, key=widget_key)
                
                elif 'Radio' in widget_type:
                    current_value = entry.get(field, False)
                    updates[field] = st.radio(label, [True, False], index=int(not current_value), key=widget_key)
                
                elif 'Date' in widget_type:
                    current_value = entry.get(field)
                    try:
                        parsed_date = pd.to_datetime(current_value, errors='coerce')
                        default_date = parsed_date.date() if not pd.isna(parsed_date) else datetime.date.today()
                    except:
                        default_date = datetime.date.today()
                    updates[field] = st.date_input(label, value=default_date, key=widget_key)
                
                else:
                    current_value = entry.get(field, '')
                    updates[field] = st.text_input(label, value=str(current_value), key=widget_key)

            col_index = (col_index + 1) % 2

# Fonction de création d'un nouvel établissement
def create_new_establishment():
    global df  # Déclaration globale au début de la fonction
    st.subheader("➕ Créer un Nouvel Établissement")
    with st.form("create_form"):
        updates = {}
        errors = []
        
        # Générer un nouvel ID unique
        new_id = str(uuid.uuid4())
        default_entry = {col: '' for col in df.columns}
        default_entry['_id'] = new_id
        default_entry['legal_status'] = OPTIONS_CONFIG['legal_status'][0]
        default_entry['isViaTrajectoire'] = False
        default_entry['updatedAt'] = datetime.datetime.now().isoformat()

        # Dans le formulaire de création
        create_form_section(
            "Informations Générales", 
            SECTION_CONFIG["📌 Informations Générales"], 
            default_entry, 
            updates, 
            key_prefix=f"create_main_{new_id}"  # Utilisation du nouvel ID unique
        )

        with st.expander("Types d'Établissement"):
            create_form_section(
                "", 
                SECTION_CONFIG["🏷️ Types d'Établissement"], 
                default_entry, 
                updates, 
                key_prefix=f"create_types_{new_id}"
            )

        with st.expander("Coordonnées"):
            create_form_section(
                "", 
                SECTION_CONFIG["📍 Coordonnées"], 
                default_entry, 
                updates, 
                key_prefix=f"create_coords_{new_id}"
            )

        with st.expander("Prix"):
            tab1, tab2 = st.tabs(["EHPAD", "Résidence Autonomie"])
            with tab1:
                create_form_section(
                    "", 
                    SECTION_CONFIG["💰 Prix EHPAD"], 
                    default_entry, 
                    updates, 
                    key_prefix=f"create_ehpad_{new_id}"
                )
            with tab2:
                create_form_section(
                    "", 
                    SECTION_CONFIG["📊 Prix Résidence Autonomie"], 
                    default_entry, 
                    updates, 
                    key_prefix=f"create_ra_{new_id}"
                )

        if st.form_submit_button("🚀 Créer l'Établissement", use_container_width=True):
            # Validation
            for field in mandatory_fields[mandatory_fields == 1].index:
                if not updates.get(field, ''):
                    errors.append(f"Champ obligatoire manquant: {field.split('.')[-1]}")
            
            for field, value in updates.items():
                widget_type = widget_types.get(field, 'Char 256')
                if not validate_input(value, widget_type, mandatory_fields.get(field, 0)):
                    errors.append(f"Format invalide pour {field.split('.')[-1]}")

            if not errors:
                new_df = pd.DataFrame([updates])
                df = pd.concat([df, new_df], ignore_index=True)
                save_data(df, "./data/base-etablissement.json")
                st.success("Établissement créé avec succès!")
                st.experimental_rerun()
            else:
                st.error("### ❌ Erreurs à corriger :")
                for error in errors:
                    st.error(f"- {error}")

# Fonction de modification d'un établissement existant
def modify_establishment():
    st.subheader("✏️ Modifier un Établissement")
    selected_id = st.selectbox("Sélectionnez un établissement", options=[""] + list(df["_id"].unique()))
    
    if selected_id:
        entry = df[df["_id"] == selected_id].iloc[0].to_dict()
        updates = {}
        errors = []
        
        with st.form(f"modify_{selected_id}"):
            # Dans le formulaire de modification
            form_id = str(selected_id).replace("-", "_")
            create_form_section(
                "Informations Générales", 
                SECTION_CONFIG["📌 Informations Générales"], 
                entry, 
                updates, 
                key_prefix=f"modify_main_{form_id}"
            )

            with st.expander("Types d'Établissement"):
                create_form_section(
                    "", 
                    SECTION_CONFIG["🏷️ Types d'Établissement"], 
                    entry, 
                    updates, 
                    key_prefix=f"modify_types_{form_id}"
                )

            with st.expander("Coordonnées"):
                create_form_section(
                    "", 
                    SECTION_CONFIG["📍 Coordonnées"], 
                    entry, 
                    updates, 
                    key_prefix=f"modify_coords_{form_id}"
                )

            with st.expander("Prix"):
                tab1, tab2 = st.tabs(["EHPAD", "Résidence Autonomie"])
                with tab1:
                    create_form_section(
                        "", 
                        SECTION_CONFIG["💰 Prix EHPAD"], 
                        entry, 
                        updates, 
                        key_prefix=f"modify_ehpad_{form_id}"
                    )
                with tab2:
                    create_form_section(
                        "", 
                        SECTION_CONFIG["📊 Prix Résidence Autonomie"], 
                        entry, 
                        updates, 
                        key_prefix=f"modify_ra_{form_id}"
                    )

            if st.form_submit_button("💾 Sauvegarder les Modifications", use_container_width=True):
                # Validation
                for field in mandatory_fields[mandatory_fields == 1].index:
                    if not updates.get(field, ''):
                        errors.append(f"Champ obligatoire manquant: {field.split('.')[-1]}")

                for field, value in updates.items():
                    widget_type = widget_types.get(field, 'Char 256')
                    if not validate_input(value, widget_type, mandatory_fields.get(field, 0)):
                        errors.append(f"Format invalide pour {field.split('.')[-1]}")

                if not errors:
                    df.loc[df['_id'] == selected_id] = pd.Series(updates)
                    save_data(df, "./data/base-etablissement.json")
                    st.success("Modifications sauvegardées avec succès!")
                else:
                    st.error("### ❌ Erreurs à corriger :")
                    for error in errors:
                        st.error(f"- {error}")

# Affichage des deux fonctionnalités côte à côte
col1, col2 = st.columns(2)
with col1:
    modify_establishment()
with col2:
    create_new_establishment()

# Affichage des données brutes
st.subheader("📊 Données Brutes")
st.dataframe(df, height=300, use_container_width=True)