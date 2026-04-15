import streamlit as st
import pandas as pd
import random
import os
from PIL import Image

st.set_page_config(page_title="Jeu de l'Oie Pédagogique", layout="wide")

# --- CONFIGURATION ---
ID_QUESTIONS = "1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E"
ID_SCORES = "1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc"
URL_SCORES = f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit"
NOM_FICHIER_QR = "qr_code.png"

def read_gsheet(file_id, sheet_name):
    cache_bust = random.randint(1, 99999)
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}&x={cache_bust}"
    return pd.read_csv(url)

@st.cache_data(ttl=10)
def get_tab_names(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    return pd.ExcelFile(url).sheet_names

# --- GESTION DU COURS ACTIF ---
tabs = get_tab_names(ID_QUESTIONS)
try:
    config_df = read_gsheet(ID_SCORES, "Config")
    instance_forcee = str(config_df.columns[0]).strip()
except:
    instance_forcee = tabs[0]

# --- INTERFACE LATÉRALE ---
st.sidebar.title("🎲 Configuration")
role = st.sidebar.radio("Mon Rôle :", ["Étudiant", "Professeur"])

if role == "Professeur":
    instance = st.sidebar.selectbox("Choisir le cours :", tabs, index=tabs.index(instance_forcee) if instance_forcee in tabs else 0)
    st.session_state['active_instance'] = instance
else:
    instance = instance_forcee
    st.sidebar.success(f"Cours actif : **{instance}**")

nom_utilisateur = st.sidebar.text_input("Votre Nom :")

if role == "Étudiant" and not nom_utilisateur:
    st.info("👋 **Bienvenue !** Entrez votre nom dans le menu à gauche pour rejoindre la partie.")
    st.stop()

# --- CHARGEMENT QUESTIONS ---
try:
    df_questions = read_gsheet(ID_QUESTIONS, instance)
    df_questions.columns = [str(c).strip() for c in df_questions.columns]
    MAX_CASES = int(df_questions['Case'].max())
except:
    st.error(f"Impossible de charger l'onglet '{instance}'.")
    st.stop()

# --- LOGIQUE ÉTUDIANT ---
if role == "Étudiant":
    st.title(f"📍 Parcours : {instance}")
    
    try:
        df_scores = read_gsheet(ID_SCORES, instance)
        df_scores.columns = [str(c).strip() for c in df_scores.columns]
        if nom_utilisateur in df_scores["Étudiant"].values:
            current_pos = int(df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"].values[0])
        else:
            current_pos = 0
    except:
        df_scores = pd.DataFrame(columns=["Étudiant", "Position"])
        current_pos = 0

    st.metric("Ma position", f"Case {current_pos} / {MAX_CASES}")

    if 'temp_pos' not in st.session_state:
        if st.button("🎲 Lancer le dé"):
            de = random.randint(1, 6)
            st.session_state.temp_pos = min(current_pos + de, MAX_CASES)
            st.rerun()
    else:
        pos = st.session_state.temp_pos
        st.subheader(f"🚀 Case visée : {pos}")
        q_data = df_questions[df_questions['Case'] == pos]
        
        if not q_data.empty:
            q_row = q_data.iloc[0]
            if 'reponse_validee' not in st.session_state:
                with
