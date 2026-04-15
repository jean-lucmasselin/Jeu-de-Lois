import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Jeu de l'Oie Pédagogique", layout="wide")

# --- CONFIGURATION ---
ID_QUESTIONS = "1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E"
ID_SCORES = "1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc"

def read_gsheet(file_id, sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

@st.cache_data(ttl=60)
def get_tab_names(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    all_sheets = pd.ExcelFile(url)
    return all_sheets.sheet_names

# --- INTERFACE ---
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

# --- CHARGEMENT ---
try:
    df_questions = read_gsheet(ID_QUESTIONS, instance)
    df_questions.columns = [str(c).strip() for c in df_questions.columns]
    
    if 'Case' not in df_questions.columns:
        st.error(f"La colonne 'Case' est absente de l'onglet {instance}.")
        st.stop()
        
    MAX_CASES = int(df_questions['Case'].max())
except Exception as e:
    st.sidebar.error(f"Erreur de chargement : {e}")
    st.stop()

# --- LOGIQUE ÉTUDIANT ---
if role == "Étudiant" and nom_utilisateur:
    st.title(f"📍 Parcours : {instance}")
    
    try:
        df_scores = read_gsheet(ID_SCORES, instance)
        df_scores.columns = [str(c).strip() for c in df_scores.columns]
        current_pos = int(df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"].values[0]) if nom_utilisateur in df_scores["Étudiant"].values else 0
    except:
        df_scores = pd.DataFrame(columns=["Étudiant", "Position"])
        current_pos = 0

    st.metric("Ma position", f"Case {current_pos} / {MAX_CASES}")

    if 'temp_pos' not in st.session_state:
        if st.button("🎲 Lancer le dé pour progresser"):
            de = random.randint(1, 6)
            st.session_state.temp_pos = min(current_pos + de, MAX_CASES)
            st.rerun()
    else:
        pos = st.session_state.temp_pos
        st.subheader(f"🚀 Case visée : {pos}")

        question_data = df_questions[df_questions['Case'] == pos]
        
        if not question_data.empty:
            q_row = question_data.iloc[0]
            
            with st.form("quiz_form"):
                st.write(f"**Question :** {q_row['Question']}")
                options = [str(q_row['A']), str(q_row['B']), str(q_row['C'])]
                choix = st.radio("Votre réponse :", options)
                
                if st.form_submit_button("Valider la réponse"):
                    map_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                    bonne_rep_lettre = str(q_row['Bonne']).strip().upper()
                    
                    if map_inv[choix] == bonne_rep_lettre:
                        st.success(f"✨ Bravo {nom_utilisateur} ! Bonne réponse.")
                        new_pos = pos
                    else:
                        new_pos = max(0, current_pos - 1)
                        st.error(f"❌ Dommage ! La bonne réponse était la **
