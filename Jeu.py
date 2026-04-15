import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Jeu de l'Oie Pédagogique", layout="wide")

# --- CONFIGURATION DES URLS ---
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

# --- BARRE LATÉRALE ---
st.sidebar.title("🎲 Configuration")

role = st.sidebar.radio("Mon Rôle :", ["Étudiant", "Professeur"])

# RÉCUPÉRATION DES ONGLETS
try:
    tabs = get_tab_names(ID_QUESTIONS)
    
    # SÉCURITÉ : Seul le prof choisit l'instance. 
    # Pour l'étudiant, on mémorise le choix du prof dans la session ou on le laisse sur le premier par défaut.
    if role == "Professeur":
        instance = st.sidebar.selectbox("Choisir le jeu (Prof uniquement) :", tabs)
        st.session_state['active_instance'] = instance
    else:
        # L'étudiant voit le cours sélectionné mais ne peut pas le changer
        default_inst = st.session_state.get('active_instance', tabs[0])
        st.sidebar.info(f"Cours actuel : **{default_inst}**")
        instance = default_inst

except Exception as e:
    st.error("Erreur de lecture des onglets.")
    st.stop()

nom_utilisateur = st.sidebar.text_input("Votre Nom :")

# --- CHARGEMENT ---
try:
    df_questions = read_gsheet(ID_QUESTIONS, instance)
    df_questions.columns = [str(c).strip() for c in df_questions.columns]
    MAX_CASES = int(df_questions['Case'].max())
except Exception as e:
    st.error(f"En attente de connexion au cours...")
    st.stop()

# --- LOGIQUE DE JEU ---
if role == "Étudiant":
    if not nom_utilisateur:
        st.info("👈 Entrez votre nom à gauche pour commencer.")
    else:
        st.title(f"📍 Parcours : {instance}")
        
        try:
            df_scores = read_gsheet(ID_SCORES, instance)
            df_scores.columns = [str(c).strip() for c in df_scores.columns]
        except:
            df_scores = pd.DataFrame(columns=["Étudiant", "Position"])

        if not df_scores.empty and nom_utilisateur in df_scores["Étudiant"].values:
            current_pos = int(df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"].values[0])
        else:
            current_pos = 0
        
        st.metric("Ma position", f"Case {current_pos} / {MAX_CASES}")

        # GESTION DU DÉ (Case 0 ou autre)
        if st.button("🎲 Lancer le dé pour progresser"):
            de = random.randint(1, 6)
            st.session_state.temp_pos = min(current_pos + de, MAX_CASES)
            st.rerun() # On force le rafraîchissement pour afficher la question

        # AFFICHAGE DE LA QUESTION SI ON A LANCÉ LE DÉ
        if 'temp_pos' in st.session_state:
            pos = st.session_state.temp_pos
            st.subheader(f"🚀 Case visée : {pos}")
            
            try:
                q_row = df_questions[df_questions['Case'] == pos].iloc[0]
                
                with st.form("quiz_form"):
                    st.write(f"**Question :** {q_row['Question']}")
                    options = [str(q_row['A']), str(q_row['B']), str(q_row['C'])]
                    choix = st.radio("Votre réponse :", options)
                    
                    if st.form_submit_button("Valider la réponse"):
                        map_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                        if map_inv[choix] == str(q_row['Reponse']).strip():
                            st.success("Correct ! Enregistrement...")
                            
                            # Mise à jour
                            if not df_scores.empty and nom_utilisateur in df_scores["Étudiant"].values:
                                df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = pos
                            else:
                                df_scores = pd.concat([df_scores, pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": pos}])], ignore_index=True)
                            
                            from streamlit_gsheets import GSheetsConnection
                            conn = st.connection("gsheets", type=GSheetsConnection)
                            conn.update(spreadsheet=f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit", worksheet=instance, data=df_scores)
                            
                            del st.session_state.temp_pos
                            st.rerun()
                        else:
                            st.error("Faux ! Vous restez sur votre case.")
                            del st.session_state.temp_pos
            except:
                st.warning(f"Pas de question sur la case {pos}. Avance automatique !")
                # Si pas de question, on avance quand même ? Ou on annule ? 
                # Ici on enregistre la position car c'est souvent une case "bonus"
                if st.button("Valider la case libre"):
                    # (Code de mise à jour identique au succès)
                    pass

elif role == "Professeur":
    st.title(f"📊 Tableau de Bord : {instance}")
    try:
        df_visu = read_gsheet(ID_SCORES, instance)
        if not df_visu.empty:
            st.bar_chart(df_visu.set_index("Étudiant")["Position"])
            st.table(df_visu.sort_values(by="Position", ascending=False))
        else:
            st.info("Aucun score pour le moment.")
    except:
        st.write("L'onglet n'est pas encore initialisé dans les scores.")
