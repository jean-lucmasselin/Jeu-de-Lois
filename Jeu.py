import streamlit as st
import pandas as pd
import random

# Gestion des imports
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    from streamlit_gsheets import GSheetConnection as GSheetsConnection

st.set_page_config(page_title="Jeu de l'Oie Pro", layout="wide")

# --- CONFIGURATION DES URLS (Nettoyées) ---
URL_QUESTIONS = "https://docs.google.com/spreadsheets/d/1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E/edit#gid=0"
URL_SCORES = "https://docs.google.com/spreadsheets/d/1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc/edit#gid=0"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- FONCTION : RÉCUPÉRER TOUS LES ONGLETS ---
@st.cache_data(ttl=60)
def get_sheet_names(url):
    # Cette astuce permet de lister les onglets sans charger tout le contenu
    sheet_id = url.split("/d/")[1].split("/")[0]
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid=0"
    # On force la lecture de la liste des onglets via pandas
    all_sheets = pd.ExcelFile(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx")
    return all_sheets.sheet_names

# --- INTERFACE LATÉRALE ---
st.sidebar.title("🎲 Configuration")

try:
    # Récupération automatique des onglets du fichier Questions
    onglets_disponibles = get_sheet_names(URL_QUESTIONS)
    instance = st.sidebar.selectbox("Choisir le cours :", onglets_disponibles)
except Exception as e:
    st.error("Erreur lors de la lecture des onglets. Vérifiez le partage du fichier Questions.")
    st.stop()

nom_utilisateur = st.sidebar.text_input("Votre Nom :")
role = st.sidebar.radio("Rôle :", ["Étudiant", "Professeur"])

# --- CHARGEMENT DES QUESTIONS ---
try:
    # On charge l'onglet sélectionné
    df_questions = conn.read(spreadsheet=URL_QUESTIONS, worksheet=instance, ttl=0)
    df_questions.columns = [str(c).strip() for c in df_questions.columns]
    
    if 'Case' not in df_questions.columns:
        st.error(f"L'onglet '{instance}' n'a pas de colonne 'Case'.")
        st.stop()
    
    MAX_CASES = int(df_questions['Case'].max())
except Exception as e:
    st.error(f"Erreur technique : {e}")
    st.stop()

# --- LOGIQUE DE JEU ---
if role == "Étudiant":
    if not nom_utilisateur:
        st.info("👈 Entrez votre nom dans le menu à gauche.")
    else:
        st.title(f"📍 Instance : {instance}")
        
        # Lecture des scores (avec création d'onglet virtuel si erreur)
        try:
            df_scores = conn.read(spreadsheet=URL_SCORES, worksheet=instance, ttl=0)
            df_scores.columns = [str(c).strip() for c in df_scores.columns]
        except:
            # Si l'onglet n'existe pas dans Scores, on l'initialise
            df_scores = pd.DataFrame(columns=["Étudiant", "Position"])

        # Position actuelle
        if nom_utilisateur in df_scores["Étudiant"].values:
            current_pos = int(df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"].values[0])
        else:
            current_pos = 0
        
        st.metric("Ma position", f"Case {current_pos} / {MAX_CASES}")

        if st.button("🎲 Lancer le dé"):
            de = random.randint(1, 6)
            st.session_state.temp_pos = min(current_pos + de, MAX_CASES)
            st.info(f"Le dé indique {de}. Allez en case {st.session_state.temp_pos}")

        if 'temp_pos' in st.session_state:
            pos = st.session_state.temp_pos
            try:
                q_row = df_questions[df_questions['Case'] == pos].iloc[0]
                
                with st.form("quiz"):
                    st.subheader(f"Question Case {pos}")
                    st.write(q_row['Question'])
                    choix = st.radio("Réponse :", [str(q_row['A']), str(q_row['B']), str(q_row['C'])])
                    
                    if st.form_submit_button("Valider"):
                        map_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                        if map_inv[choix] == str(q_row['Reponse']).strip():
                            st.success("Correct !")
                            # Mise à jour locale
                            if nom_utilisateur in df_scores["Étudiant"].values:
                                df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = pos
                            else:
                                df_scores = pd.concat([df_scores, pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": pos}])])
                            
                            # Envoi vers Google (crée l'onglet si nécessaire)
                            conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=df_scores)
                            del st.session_state.temp_pos
                            st.rerun()
                        else:
                            st.error("Faux ! Vous n'avancez pas.")
                            del st.session_state.temp_pos
            except:
                st.warning("Pas de question sur cette case.")

elif role == "Professeur":
    st.title(f"📊 Suivi : {instance}")
    try:
        df_visu = conn.read(spreadsheet=URL_SCORES, worksheet=instance, ttl=0)
        if not df_visu.empty:
            st.bar_chart(df_visu.set_index("Étudiant")["Position"])
            st.table(df_visu.sort_values(by="Position", ascending=False))
        else:
            st.write("Aucun joueur.")
    except:
        st.write("L'onglet de score n'est pas encore créé (il le sera dès qu'un étudiant aura répondu juste).")
