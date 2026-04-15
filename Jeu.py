import streamlit as st
import pandas as pd
import random
import os
from PIL import Image

st.set_page_config(page_title="Jeu de l'Oie Pédagogique", layout="wide")

# --- CONFIGURATION DES FICHIERS ---
ID_QUESTIONS = "1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E"
ID_SCORES = "1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc"
# Assurez-vous que ce nom correspond au fichier sur GitHub
NOM_FICHIER_QR = "qr_code.png" 

def read_gsheet(file_id, sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

@st.cache_data(ttl=60)
def get_tab_names(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    all_sheets = pd.ExcelFile(url)
    return all_sheets.sheet_names

# --- INTERFACE LATÉRALE ---
st.sidebar.title("🎲 Configuration")
role = st.sidebar.radio("Mon Rôle :", ["Étudiant", "Professeur"])
tabs = get_tab_names(ID_QUESTIONS)

if 'active_instance' not in st.session_state:
    st.session_state['active_instance'] = tabs[0]

if role == "Professeur":
    instance = st.sidebar.selectbox("Choisir le jeu :", tabs, index=tabs.index(st.session_state['active_instance']))
    st.session_state['active_instance'] = instance
else:
    instance = st.session_state['active_instance']
    st.sidebar.success(f"Cours actif : **{instance}**")

nom_utilisateur = st.sidebar.text_input("Votre Nom :")

# --- ACCUEIL ÉTUDIANT ---
if role == "Étudiant" and not nom_utilisateur:
    st.info("👋 **Bienvenue !** Veuillez ouvrir le menu à gauche (flèche en haut à gauche sur mobile) et entrer votre nom pour rejoindre la partie.")
    st.stop()

# --- CHARGEMENT DES DONNÉES ---
try:
    df_questions = read_gsheet(ID_QUESTIONS, instance)
    df_questions.columns = [str(c).strip() for c in df_questions.columns]
    MAX_CASES = int(df_questions['Case'].max())
except:
    st.info("Connexion au serveur de jeu en cours...")
    st.stop()

# --- LOGIQUE ÉTUDIANT ---
if role == "Étudiant":
    st.title(f"📍 Parcours : {instance}")
    
    # 1. Récupération du Score
    try:
        df_scores = read_gsheet(ID_SCORES, instance)
        df_scores.columns = [str(c).strip() for c in df_scores.columns]
        current_pos = int(df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"].values[0]) if nom_utilisateur in df_scores["Étudiant"].values else 0
    except:
        df_scores = pd.DataFrame(columns=["Étudiant", "Position"])
        current_pos = 0

    st.metric("Ma position actuelle", f"Case {current_pos} / {MAX_CASES}")

    # 2. Lancer le dé
    if 'temp_pos' not in st.session_state:
        if st.button("🎲 Lancer le dé"):
            de = random.randint(1, 6)
            st.session_state.temp_pos = min(current_pos + de, MAX_CASES)
            st.rerun()

    # 3. Question
    else:
        pos = st.session_state.temp_pos
        st.subheader(f"🚀 Case visée : {pos}")
        
        q_data = df_questions[df_questions['Case'] == pos]
        
        if not q_data.empty:
            q_row = q_data.iloc[0]
            
            if 'reponse_validee' not in st.session_state:
                with st.form("quiz_form"):
                    st.write(f"**Question :** {q_row['Question']}")
                    choix = st.radio("Votre réponse :", [str(q_row['A']), str(q_row['B']), str(q_row['C'])])
                    if st.form_submit_button("Valider la réponse"):
                        map_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                        bonne_rep = str(q_row['Bonne']).strip().upper()
                        
                        # Résultat
                        juste = (map_inv[choix] == bonne_rep)
                        new_pos = pos if juste else max(0, current_pos - 1)
                        
                        # --- SAUVEGARDE FORCEE ---
                        from streamlit_gsheets import GSheetsConnection
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        
                        if nom_utilisateur in df_scores["Étudiant"].values:
                            df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = new_pos
                        else:
                            df_scores = pd.concat([df_scores, pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": new_pos}])], ignore_index=True)
                        
                        conn.update(spreadsheet=f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit", worksheet=instance, data=df_scores)
                        
                        # Mémorisation du message pour affichage après rerun
                        st.session_state.reponse_validee = True
                        st.session_state.message_type = "success" if juste else "error"
                        st.session_state.message_text = f"✨ Bravo ! Bonne réponse." if juste else f"❌ Dommage ! La réponse était {bonne_rep}. Vous reculez d'une case."
                        st.rerun()

            # Affichage du résultat après validation
            if st.session_state.get('reponse_validee'):
                if st.session_state.message_type == "success":
                    st.success(st.session_state.message_text)
                else:
                    st.error(st.session_state.message_text)
                
                if st.button("Continuer (jeter à nouveau les dés)"):
                    del st.session_state.temp_pos
                    del st.session_state.reponse_validee
                    st.rerun()
        else:
            st.warning("🍃 Case libre !")
            if st.button("S'installer ici"):
                del st.session_state.temp_pos
                st.rerun()

# --- LOGIQUE PROFESSEUR ---
elif role == "Professeur":
    st.title(f"👨‍🏫 Tableau de Bord : {instance}")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        try:
            df_visu = read_gsheet(ID_SCORES, instance)
            if not df_visu.empty:
                st.bar_chart(df_visu.set_index("Étudiant")["Position"])
                st.table(df_visu.sort_values(by="Position", ascending=False))
            else:
                st.info("En attente de joueurs...")
        except:
            st.info("Aucun score enregistré.")

    with col2:
        st.subheader("QR Code")
        if os.path.exists(NOM_FICHIER_QR):
            st.image(Image.open(NOM_FICHIER_QR), use_container_width=True)
        else:
            st.error(f"Fichier {NOM_FICHIER_QR} introuvable sur GitHub.")
