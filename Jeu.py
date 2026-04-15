import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Jeu de l'Oie Pédagogique", layout="wide")

# --- CONFIGURATION DES URLS ---
# On utilise l'ID pur du fichier pour construire des URLs de téléchargement direct
ID_QUESTIONS = "1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E"
ID_SCORES = "1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc"

# Fonction pour lire n'importe quel onglet en CSV (évite l'erreur 400)
def read_gsheet(file_id, sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    return pd.read_csv(url)

# --- RÉCUPÉRATION DES ONGLETS ---
@st.cache_data(ttl=60)
def get_tab_names(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    all_sheets = pd.ExcelFile(url)
    return all_sheets.sheet_names

# --- BARRE LATÉRALE ---
st.sidebar.title("🎲 Configuration")

try:
    tabs = get_tab_names(ID_QUESTIONS)
    instance = st.sidebar.selectbox("Choisir le jeu :", tabs)
except Exception as e:
    st.error("Erreur lors de la lecture des onglets.")
    st.stop()

nom_utilisateur = st.sidebar.text_input("Votre Nom :")
role = st.sidebar.radio("Rôle :", ["Étudiant", "Professeur"])

# --- CHARGEMENT DES DONNÉES ---
try:
    # Lecture directe via l'URL CSV (beaucoup plus stable)
    df_questions = read_gsheet(ID_QUESTIONS, instance)
    df_questions.columns = [str(c).strip() for c in df_questions.columns]
    
    if 'Case' not in df_questions.columns:
        st.error(f"L'onglet '{instance}' n'a pas de colonne 'Case'.")
        st.stop()
    
    MAX_CASES = int(df_questions['Case'].max())
except Exception as e:
    st.error(f"Erreur technique (Questions) : {e}")
    st.stop()

# --- LOGIQUE DE JEU ---
if role == "Étudiant":
    if not nom_utilisateur:
        st.info("👈 Entrez votre nom à gauche.")
    else:
        st.title(f"📍 Instance : {instance}")
        
        # Lecture des scores
        try:
            df_scores = read_gsheet(ID_SCORES, instance)
            df_scores.columns = [str(c).strip() for c in df_scores.columns]
        except:
            df_scores = pd.DataFrame(columns=["Étudiant", "Position"])

        # Position actuelle
        if not df_scores.empty and nom_utilisateur in df_scores["Étudiant"].values:
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
                            if not df_scores.empty and nom_utilisateur in df_scores["Étudiant"].values:
                                df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = pos
                            else:
                                new_line = pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": pos}])
                                df_scores = pd.concat([df_scores, new_line], ignore_index=True)
                            
                            # SAUVEGARDE (On repasse par st.connection juste pour l'écriture)
                            try:
                                from streamlit_gsheets import GSheetsConnection
                                conn = st.connection("gsheets", type=GSheetsConnection)
                                conn.update(spreadsheet=f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit", worksheet=instance, data=df_scores)
                                del st.session_state.temp_pos
                                st.rerun()
                            except Exception as e_save:
                                st.error(f"Erreur lors de l'enregistrement du score : {e_save}")
                        else:
                            st.error("Faux ! Vous n'avancez pas.")
                            del st.session_state.temp_pos
            except Exception as e_q:
                st.warning(f"Pas de question sur cette case ou erreur de format : {e_q}")

elif role == "Professeur":
    st.title(f"📊 Suivi : {instance}")
    try:
        df_visu = read_gsheet(ID_SCORES, instance)
        if not df_visu.empty:
            st.bar_chart(df_visu.set_index("Étudiant")["Position"])
            st.table(df_visu.sort_values(by="Position", ascending=False))
        else:
            st.write("Aucun joueur.")
    except:
        st.write("Aucun score enregistré.")
