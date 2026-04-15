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
# NOM EXACT DU FICHIER TELECHARGE
NOM_FICHIER_QR = "qr_code.png" 

def read_gsheet(file_id, sheet_name):
    cache_bust = random.randint(1, 99999)
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}&x={cache_bust}"
    return pd.read_csv(url)

@st.cache_data(ttl=10)
def get_tab_names(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    return pd.ExcelFile(url).sheet_names

# --- GESTION DU COURS ---
try:
    tabs = get_tab_names(ID_QUESTIONS)
    config_df = read_gsheet(ID_SCORES, "Config")
    instance_forcee = str(config_df.columns[0]).strip()
except:
    tabs = ["Supervision"] # Secours
    instance_forcee = tabs[0]

# --- INTERFACE ---
st.sidebar.title("🎲 Configuration")
role = st.sidebar.radio("Mon Rôle :", ["Étudiant", "Professeur"])

if role == "Professeur":
    instance = st.sidebar.selectbox("Choisir le cours :", tabs, index=tabs.index(instance_forcee) if instance_forcee in tabs else 0)
    st.sidebar.info("Modifiez l'onglet 'Config' dans Excel pour changer le cours des étudiants.")
else:
    instance = instance_forcee
    st.sidebar.success(f"Cours : **{instance}**")

nom_utilisateur = st.sidebar.text_input("Votre Nom :")

# --- LOGIQUE ÉTUDIANT ---
if role == "Étudiant":
    if not nom_utilisateur:
        st.info("👋 **Bienvenue !** Ouvrez le menu à gauche et entrez votre nom pour commencer.")
    else:
        st.title(f"📍 Parcours : {instance}")
        
        # Chargement Questions & Scores
        try:
            df_questions = read_gsheet(ID_QUESTIONS, instance)
            df_questions.columns = [str(c).strip() for c in df_questions.columns]
            MAX_CASES = int(df_questions['Case'].max())
            
            df_scores = read_gsheet(ID_SCORES, instance)
            df_scores.columns = [str(c).strip() for c in df_scores.columns]
            current_pos = int(df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"].values[0]) if nom_utilisateur in df_scores["Étudiant"].values else 0
        except:
            current_pos = 0
            MAX_CASES = 20 # Par défaut

        st.metric("Ma position", f"Case {current_pos} / {MAX_CASES}")

        # Lancer le dé
        if 'temp_pos' not in st.session_state:
            if st.button("🎲 Lancer le dé"):
                de = random.randint(1, 6)
                st.session_state.temp_pos = min(current_pos + de, MAX_CASES)
                st.rerun()
        else:
            pos = st.session_state.temp_pos
            st.subheader(f"🚀 Case visée : {pos}")
            
            # Affichage de la question
            try:
                q_row = df_questions[df_questions['Case'] == pos].iloc[0]
                if 'reponse_validee' not in st.session_state:
                    with st.form("quiz_form"):
                        st.write(f"**Question :** {q_row['Question']}")
                        choix = st.radio("Réponse :", [str(q_row['A']), str(q_row['B']), str(q_row['C'])])
                        if st.form_submit_button("Valider la réponse"):
                            map_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                            bonne_rep = str(q_row['Bonne']).strip().upper()
                            juste = (map_inv[choix] == bonne_rep)
                            new_pos = pos if juste else max(0, current_pos - 1)
                            
                            # TENTATIVE DE SAUVEGARDE
                            try:
                                from streamlit_gsheets import GSheetsConnection
                                conn = st.connection("gsheets", type=GSheetsConnection)
                                
                                # Mise à jour locale du DataFrame avant envoi
                                if nom_utilisateur in df_scores["Étudiant"].values:
                                    df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = new_pos
                                else:
                                    new_line = pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": new_pos}])
                                    df_scores = pd.concat([df_scores, new_line], ignore_index=True)
                                
                                conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=df_scores)
                            except:
                                st.warning("⚠️ Connexion Cloud instable. Score sauvegardé pour cette session.")

                            st.session_state.reponse_validee = True
                            st.session_state.res_msg = (juste, bonne_rep, new_pos)
                            st.rerun()
                
                # Résultat
                if st.session_state.get('reponse_validee'):
                    juste, bonne_rep, new_pos = st.session_state.res_msg
                    if juste: st.success("✨ Bravo ! Bonne réponse.")
                    else: st.error(f"❌ Dommage ! La réponse était {bonne_rep}. Vous reculez d'une case (Position : {new_pos}).")
                    
                    if st.button("Continuer (jeter à nouveau les dés)"):
                        del st.session_state.temp_pos
                        del st.session_state.reponse_validee
                        st.rerun()
            except:
                st.warning("🍃 Case sans question. Avance libre !")
                if st.button("S'installer ici"):
                    del st.session_state.temp_pos
                    st.rerun()

# --- LOGIQUE PROFESSEUR ---
elif role == "Professeur":
    st.title(f"👨‍🏫 Tableau de Bord : {instance}")
    col_g, col_d = st.columns([3, 1])
    
    with col_g:
        try:
            df_v
