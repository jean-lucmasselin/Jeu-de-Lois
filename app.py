import streamlit as st
from streamlit_gsheets import GSheetsConnection  # Note le 's' à GSheets
import pandas as pd
import random

st.set_page_config(page_title="Jeu de l'Oie Connecté", layout="wide")

# URLs de vos Sheets (Remplacez la deuxième par l'URL réelle de votre fichier scores)
URL_QUESTIONS = "https://docs.google.com/spreadsheets/d/1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E/edit?usp=drivesdk"
URL_SCORES = "https://docs.google.com/spreadsheets/d/1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc/edit?usp=sharing"

# --- CONNEXION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURATION INTERFACE ---
st.sidebar.title("⚙️ Configuration")

# 1. Choix de l'instance (Onglet)
# On définit manuellement les noms d'onglets ou on les récupère
instance = st.sidebar.selectbox("Choisissez l'instance (cours) :", ["Sheet1", "Cours_B"]) # Modifiez selon vos onglets

# 2. Identification
nom_utilisateur = st.sidebar.text_input("Votre Nom :")
role = st.sidebar.radio("Rôle :", ["Étudiant", "Professeur"])

# --- CHARGEMENT DES DONNÉES ---
df_questions = conn.read(spreadsheet=URL_QUESTIONS, worksheet=instance)
MAX_CASES = df_questions['Case'].max()

def get_scores():
    try:
        return conn.read(spreadsheet=URL_SCORES, worksheet=instance)
    except:
        return pd.DataFrame(columns=["Étudiant", "Position"])

def update_score(nom, nouvelle_pos):
    scores = get_scores()
    if nom in scores["Étudiant"].values:
        scores.loc[scores["Étudiant"] == nom, "Position"] = nouvelle_pos
    else:
        new_row = pd.DataFrame({"Étudiant": [nom], "Position": [nouvelle_pos]})
        scores = pd.concat([scores, new_row], ignore_index=True)
    
    # Mise à jour de la Google Sheet
    conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=scores)

# --- LOGIQUE DE JEU ---
if role == "Étudiant":
    if not nom_utilisateur:
        st.warning("Entrez votre nom à gauche.")
    else:
        st.title(f"Instance : {instance}")
        scores_actuels = get_scores()
        current_pos = scores_actuels.loc[scores_actuels["Étudiant"] == nom_utilisateur, "Position"].values[0] if nom_utilisateur in scores_actuels["Étudiant"].values else 0
        
        st.metric("Position", f"Case {current_pos}")

        if st.button("🎲 Lancer le dé"):
            de = random.randint(1, 6)
            st.session_state.temp_pos = min(current_pos + de, MAX_CASES)
            st.info(f"Vous avancez vers la case {st.session_state.temp_pos}")

        if 'temp_pos' in st.session_state:
            pos = st.session_state.temp_pos
            q_data = df_questions[df_questions['Case'] == pos].iloc[0]
            st.subheader(f"Question {pos}")
            st.write(q_data['Question'])
            choix = st.radio("Réponse :", [q_data['A'], q_data['B'], q_data['C']])
            
            if st.button("Valider"):
                mapping = {q_data['A']: 'A', q_data['B']: 'B', q_data['C']: 'C'}
                if mapping[choix] == q_data['Reponse']:
                    st.success("Bravo !")
                    update_score(nom_utilisateur, pos)
                else:
                    st.error("Dommage...")
                del st.session_state.temp_pos
                st.rerun()

elif role == "Professeur":
    st.title(f"Suivi : {instance}")
    scores = get_scores()
    if not scores.empty:
        import plotly.express as px
        fig = px.scatter(scores, x="Position", y="Étudiant", color="Étudiant")
        fig.update_xaxes(range=[0, MAX_CASES + 1])
        st.plotly_chart(fig)
        st.table(scores)
