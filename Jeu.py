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
# Assurez-vous que ce nom est exact sur GitHub
NOM_FICHIER_QR = "QR_code.png" 

def read_gsheet(file_id, sheet_name):
    # Cache bust pour forcer la lecture de la donnée fraîche
    cb = random.randint(1, 99999)
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}&x={cb}"
    return pd.read_csv(url)

@st.cache_data(ttl=10)
def get_tab_names(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    return pd.ExcelFile(url).sheet_names

# --- LOGIQUE DE CONFIGURATION INITIALE ---
try:
    tabs = get_tab_names(ID_QUESTIONS)
    config_df = read_gsheet(ID_SCORES, "Config")
    # On récupère le nom du cours actif dans la première colonne de l'onglet Config
    instance_forcee = str(config_df.columns[0]).strip()
except:
    tabs = ["Supervision"] 
    instance_forcee = "Supervision"

# --- INTERFACE LATERALE ---
st.sidebar.title("🎲 Configuration")
role = st.sidebar.radio("Mon Rôle :", ["Étudiant", "Professeur"])

if role == "Professeur":
    instance = st.sidebar.selectbox("Cours sélectionné :", tabs, index=tabs.index(instance_forcee) if instance_forcee in tabs else 0)
else:
    instance = instance_forcee
    st.sidebar.success(f"Cours actuel : **{instance}**")

nom_utilisateur = st.sidebar.text_input("Votre Nom :")

# --- SECTION PROFESSEUR ---
if role == "Professeur":
    st.title(f"👨‍🏫 Tableau de Bord : {instance}")
    col_g, col_d = st.columns([3, 1])
    
    with col_g:
        try:
            df_v = read_gsheet(ID_SCORES, instance)
            if not df_v.empty:
                df_v.columns = [str(c).strip() for c in df_v.columns]
                st.subheader("Progression des élèves")
                st.bar_chart(df_v.set_index("Étudiant")["Position"])
                st.table(df_v.sort_values(by="Position", ascending=False))
            else:
                st.info("En attente des premiers joueurs...")
        except:
            st.info("Aucun score enregistré pour cet onglet.")

    with col_d:
        st.subheader("Accès au jeu")
        if os.path.exists(NOM_FICHIER_QR):
            st.image(Image.open(NOM_FICHIER_QR), use_container_width=True)
        else:
            st.error("Fichier QR Code absent sur GitHub.")

# --- SECTION ÉTUDIANT ---
elif role == "Étudiant":
    if not nom_utilisateur:
        st.info("👋 **Bienvenue !** Ouvrez le menu à gauche et entrez votre nom pour commencer.")
    else:
        st.title(f"📍 Parcours : {instance}")
        
        # Chargement Questions & Scores
        try:
            df_q = read_gsheet(ID_QUESTIONS, instance)
            df_q.columns = [str(c).strip() for c in df_q.columns]
            
            df_s = read_gsheet(ID_SCORES, instance)
            df_s.columns = [str(c).strip() for c in df_s.columns]
            
            curr_pos = int(df_s.loc[df_s["Étudiant"] == nom_utilisateur, "Position"].values[0]) if nom_utilisateur in df_s["Étudiant"].values else 0
            max_c = int(df_q['Case'].max())
        except:
            curr_pos = 0
            max_c = 20

        st.metric("Ma position", f"Case {curr_pos} / {max_c}")

        # Phase 1 : Lancer le dé
        if 'temp_pos' not in st.session_state:
            if st.button("🎲
