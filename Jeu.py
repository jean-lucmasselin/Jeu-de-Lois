import streamlit as st
import pandas as pd
import random

try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    from streamlit_gsheets import GSheetConnection as GSheetsConnection

st.set_page_config(page_title="Jeu de l'Oie Dynamique", layout="wide")

# --- CONFIGURATION DES URLS ---
URL_QUESTIONS = "https://docs.google.com/spreadsheets/d/1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E/edit"
URL_SCORES = "https://docs.google.com/spreadsheets/d/1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc/edit"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FONCTION POUR RÉCUPÉRER LES ONGLETS ---
@st.cache_data(ttl=600)
def get_all_sheets(url):
    # Cette astuce permet de lister les onglets sans erreur
    sheet_id = url.split("/d/")[1].split("/")[0]
    api_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
    # On lit juste pour tester la connexion et on pourrait affiner, 
    # mais pour faire simple, liste tes onglets ici si l'API est bloquée :
    return ["Supervision", "CG04", "CG05"] # <--- MODIFIE CES NOMS ICI selon ton Excel

# --- INTERFACE ---
st.sidebar.title("🎮 Configuration")

# --- CONFIGURATION DES ONGLETS ---
liste_onglets = ["Supervision", "CG04", "CG05"]
instance = st.sidebar.selectbox("Choisir le jeu :", liste_onglets)

# --- CHARGEMENT ---
try:
    # On force la lecture en ignorant le cache pour le test
    df_questions = conn.read(spreadsheet=URL_QUESTIONS, worksheet=instance, ttl=0)
    st.sidebar.success(f"✅ Onglet {instance} Questions : OK")
    
    # Tentative de lecture des scores
    try:
        df_scores = conn.read(spreadsheet=URL_SCORES, worksheet=instance, ttl=0)
        st.sidebar.success(f"✅ Onglet {instance} Scores : OK")
    except Exception as e_score:
        st.sidebar.warning("⚠️ Onglet Scores vide ou inexistant. Création auto prévue.")
        df_scores = pd.DataFrame(columns=["Étudiant", "Position"])

except Exception as e:
    st.error("❌ Erreur de connexion détaillée :")
    st.code(str(e)) # Ceci va nous dire EXACTEMENT ce qui ne va pas
    st.info("Vérifiez que le nom de l'onglet est EXACTEMENT le même dans Excel et dans le menu de gauche.")
    st.stop()
instance = st.sidebar.selectbox("Choisir le cours :", liste_onglets)
nom_utilisateur = st.sidebar.text_input("Ton Nom :")
role = st.sidebar.radio("Rôle :", ["Étudiant", "Professeur"])

# --- CHARGEMENT DES DONNÉES ---
try:
    # Lecture directe sans passer par des fonctions complexes
    df_questions = conn.read(spreadsheet=URL_QUESTIONS, worksheet=instance)
    # On force le nom des colonnes en majuscule/nettoyé
    df_questions.columns = [str(c).strip() for c in df_questions.columns]
    
    if 'Case' not in df_questions.columns:
        st.error(f"L'onglet '{instance}' ne semble pas avoir de colonne 'Case'.")
        st.stop()
        
    MAX_CASES = int(df_questions['Case'].max())
    
    # ... reste du code (Etudiant / Professeur) ...

    if role == "Étudiant":
        if not nom_utilisateur:
            st.info("👈 Entre ton nom dans le menu à gauche pour commencer.")
        else:
            st.title(f"📍 Parcours : {instance}")
            
            # Lecture des scores
            try:
                scores_df = conn.read(spreadsheet=URL_SCORES, worksheet=instance)
            except:
                scores_df = pd.DataFrame(columns=["Étudiant", "Position"])

            current_pos = scores_df.loc[scores_df["Étudiant"] == nom_utilisateur, "Position"].values[0] if nom_utilisateur in scores_df["Étudiant"].values else 0
            
            st.metric("Ma position", f"Case {current_pos} / {MAX_CASES}")

            if st.button("🎲 Lancer le dé"):
                de = random.randint(1, 6)
                st.session_state.temp_pos = min(current_pos + de, MAX_CASES)
                st.write(f"Le dé indique {de} ! Tu vas à la case {st.session_state.temp_pos}")

            if 'temp_pos' in st.session_state:
                pos = st.session_state.temp_pos
                q_row = df_questions[df_questions['Case'] == pos].iloc[0]
                
                with st.form("question_form"):
                    st.subheader(f"❓ Question Case {pos}")
                    st.write(q_row['Question'])
                    choix = st.radio("Ta réponse :", [q_row['A'], q_row['B'], q_row['C']])
                    submit = st.form_submit_button("Valider")
                    
                    if submit:
                        mapping = {q_row['A']: 'A', q_row['B']: 'B', q_row['C']: 'C'}
                        if mapping[choix] == q_row['Reponse']:
                            st.success("Bonne réponse ! Tu avances.")
                            # Mise à jour du score
                            new_scores = scores_df.copy()
                            if nom_utilisateur in new_scores["Étudiant"].values:
                                new_scores.loc[new_scores["Étudiant"] == nom_utilisateur, "Position"] = pos
                            else:
                                new_scores = pd.concat([new_scores, pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": pos}])])
                            
                            conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=new_scores)
                            del st.session_state.temp_pos
                            st.rerun()
                        else:
                            st.error("Mauvaise réponse... Tu restes sur ta case.")
                            del st.session_state.temp_pos

    elif role == "Professeur":
        st.title(f"📊 Suivi : {instance}")
        try:
            scores_visu = conn.read(spreadsheet=URL_SCORES, worksheet=instance)
            if not scores_visu.empty:
                st.bar_chart(scores_visu.set_index("Étudiant")["Position"])
                st.table(scores_visu)
            else:
                st.write("En attente de joueurs...")
        except:
            st.write("Aucune donnée de score trouvée pour cet onglet.")

except Exception as e:
    st.error(f"Erreur de connexion : {e}")
    st.info("Vérifiez que l'onglet sélectionné existe et que le fichier est bien partagé.")
