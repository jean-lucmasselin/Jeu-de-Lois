import streamlit as st
import pandas as pd
import random
import os

# Configuration de la page
st.set_page_config(page_title="Jeu de l'Oie Éducatif", layout="wide")

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_questions():
    return pd.read_excel("questions.xlsx")

df_questions = load_questions()
MAX_CASES = df_questions['Case'].max()

# --- GESTION DU SCORE (Fichier CSV local) ---
SCORE_FILE = "scores.csv"
if not os.path.exists(SCORE_FILE):
    pd.DataFrame(columns=["Étudiant", "Position"]).to_csv(SCORE_FILE, index=False)

def get_scores():
    return pd.read_csv(SCORE_FILE)

def update_score(nom, nouvelle_pos):
    scores = get_scores()
    if nom in scores["Étudiant"].values:
        scores.loc[scores["Étudiant"] == nom, "Position"] = nouvelle_pos
    else:
        new_row = pd.DataFrame({"Étudiant": [nom], "Position": [nouvelle_pos]})
        scores = pd.concat([scores, new_row], ignore_index=True)
    scores.to_csv(SCORE_FILE, index=False)

# --- INTERFACE UTILISATEUR ---
st.sidebar.title("🎮 Connexion")
nom_utilisateur = st.sidebar.text_input("Entrez votre nom :")
role = st.sidebar.radio("Rôle :", ["Étudiant", "Professeur"])

if role == "Étudiant":
    if not nom_utilisateur:
        st.warning("Veuillez entrer votre nom dans la barre latérale.")
    else:
        st.title(f"Bonne chance, {nom_utilisateur} !")
        
        # Récupérer position actuelle
        scores = get_scores()
        current_pos = scores.loc[scores["Étudiant"] == nom_utilisateur, "Position"].values[0] if nom_utilisateur in scores["Étudiant"].values else 0
        
        st.metric("Ma position actuelle", f"Case {current_pos}")

        if st.button("🎲 Lancer le dé"):
            de = random.randint(1, 6)
            nouvelle_pos = min(current_pos + de, MAX_CASES)
            st.session_state.temp_pos = nouvelle_pos
            st.info(f"Le dé affiche {de}. Vous tombez sur la case {nouvelle_pos} !")

        if 'temp_pos' in st.session_state:
            pos = st.session_state.temp_pos
            q_data = df_questions[df_questions['Case'] == pos].iloc[0]
            
            st.subheader(f"Question Case {pos}")
            st.write(q_data['Question'])
            
            reponse = st.radio("Choisissez :", [q_data['A'], q_data['B'], q_data['C']])
            map_rep = {q_data['A']: 'A', q_data['B']: 'B', q_data['C']: 'C'}

            if st.button("Valider la réponse"):
                if map_rep[reponse] == q_data['Reponse']:
                    st.success("Correct ! Vous avancez.")
                    update_score(nom_utilisateur, pos)
                    del st.session_state.temp_pos
                else:
                    st.error("Mauvaise réponse... vous restez sur votre case précédente.")
                    del st.session_state.temp_pos

elif role == "Professeur":
    st.title("👨‍🏫 Tableau de Bord Enseignant")
    scores = get_scores()
    
    if not scores.empty:
        # Affichage du plateau sous forme de graphique
        import plotly.express as px
        fig = px.scatter(scores, x="Position", y="Étudiant", color="Étudiant", 
                         title="Progression en temps réel", size_max=20)
        fig.update_xaxes(range=[0, MAX_CASES + 1])
        st.plotly_chart(fig, use_container_width=True)
        
        st.table(scores.sort_values(by="Position", ascending=False))
    else:
        st.info("Aucun étudiant n'est encore connecté.")
