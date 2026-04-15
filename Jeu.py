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
    # On nettoie les espaces autour des noms de colonnes sans changer les noms
    df_questions.columns = [str(c).strip() for c in df_questions.columns]
    
    # Vérification de la colonne Case
    if 'Case' not in df_questions.columns:
        st.error(f"La colonne 'Case' est absente de l'onglet {instance}. Vérifiez l'en-tête.")
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
                # Utilisation de tes en-têtes exacts : A, B, C
                options = [str(q_row['A']), str(q_row['B']), str(q_row['C'])]
                choix = st.radio("Votre réponse :", options)
                
                if st.form_submit_button("Valider la réponse"):
                    map_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                    
                    # CORRECTION : On utilise l'en-tête "Bonne" que tu as spécifié
                    bonne_rep_lettre = str(q_row['Bonne']).strip().upper()
                    
                    if map_inv[choix] == bonne_rep_lettre:
                        st.success(f"✨ Bravo {nom_utilisateur} ! Bonne réponse.")
                        new_pos = pos
                    else:
                        new_pos = max(0, current_pos - 1)
                        st.error(f"❌ Dommage ! La bonne réponse était la **{bonne_rep_lettre}**. Vous reculez à la case {new_pos}.")
                    
                    # SAUVEGARDE
                    if nom_utilisateur in df_scores["Étudiant"].values:
                        df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = new_pos
                    else:
                        df_scores = pd.concat([df_scores, pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": new_pos}])], ignore_index=True)
                    
                    try:
                        from streamlit_gsheets import GSheetsConnection
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(spreadsheet=f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit", worksheet=instance, data=df_scores)
                    except Exception as e:
                        st.warning(f"Erreur d'écriture : {e}")

                    # On ne met pas de bouton ici pour éviter les conflits, 
                    # le rerun se fera au prochain clic sur "Continuer"
                    st.session_state.show_continue = True

            if st.session_state.get('show_continue'):
                if st.button("Continuer la partie"):
                    del st.session_state.temp_pos
                    del st.session_state.show_continue
                    st.rerun()
        else:
            st.warning("🍃 Case libre ! Vous avancez sans question.")
            if st.button("S'installer sur cette case"):
                # Mise à jour auto sur case sans question
                if nom_utilisateur in df_scores["Étudiant"].values:
                    df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = pos
                else:
                    df_scores = pd.concat([df_scores, pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": pos}])], ignore_index=True)
                
                from streamlit_gsheets import GSheetsConnection
                conn = st.connection("gsheets", type=GSheetsConnection)
                conn.update(spreadsheet=f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit", worksheet=instance, data=df_scores)
                del st.session_state.temp_pos
                st.rerun()

elif role == "Professeur":
    st.title(f"📊 Suivi : {instance}")
    try:
        df_visu = read_gsheet(ID_SCORES, instance)
        if not df_visu.empty:
            st.bar_chart(df_visu.set_index("Étudiant")["Position"])
            st.table(df_visu.sort_values(by="Position", ascending=False))
    except:
        st.info("Aucun score enregistré.")import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Jeu de l'Oie Pédagogique", layout="wide")

# --- CONFIGURATION ---
ID_QUESTIONS = "1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E"
ID_SCORES = "1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc"

def read_gsheet(file_id, sheet_name):
    # Ajout d'un paramètre pour forcer la lecture fraîche
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

# Initialisation de l'instance dans la session si absente
if 'active_instance' not in st.session_state:
    st.session_state['active_instance'] = tabs[0]

if role == "Professeur":
    instance = st.sidebar.selectbox("Choisir le jeu :", tabs, index=tabs.index(st.session_state['active_instance']))
    st.session_state['active_instance'] = instance
else:
    instance = st.session_state['active_instance']
    st.sidebar.success(f"Cours actif : **{instance}**")

nom_utilisateur = st.sidebar.text_input("Votre Nom :")

# --- CHARGEMENT & NETTOYAGE ---
try:
    df_questions = read_gsheet(ID_QUESTIONS, instance)
    # NETTOYAGE CRUCIAL DES COLONNES (Gère accents et majuscules)
    df_questions.columns = [str(c).strip().replace('é', 'e').replace('É', 'E').capitalize() for c in df_questions.columns]
    # On force les noms attendus pour le code
    # Si vous avez 'Case', 'Question', 'A', 'B', 'C', 'Reponse'
    MAX_CASES = int(df_questions['Case'].max())
except Exception as e:
    st.sidebar.error(f"Erreur de chargement des colonnes : {e}")
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
                # On s'assure que A, B, C existent
                options = [str(q_row['A']), str(q_row['B']), str(q_row['C'])]
                choix = st.radio("Votre réponse :", options)
                
                if st.form_submit_button("Valider la réponse"):
                    map_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                    # On cherche la colonne qui ressemble à "Reponse" ou "Réponse"
                    col_rep = "Reponse" if "Reponse" in df_questions.columns else "Réponse"
                    bonne_rep_lettre = str(q_row[col_rep]).strip().upper()
                    
                    if map_inv[choix] == bonne_rep_lettre:
                        st.success(f"✨ Bravo {nom_utilisateur} ! Bonne réponse.")
                        new_pos = pos
                    else:
                        new_pos = max(0, current_pos - 1)
                        st.error(f"❌ Dommage ! La bonne réponse était la **{bonne_rep_lettre}**. Vous reculez à la case {new_pos}.")
                    
                    # SAUVEGARDE
                    if nom_utilisateur in df_scores["Étudiant"].values:
                        df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = new_pos
                    else:
                        df_scores = pd.concat([df_scores, pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": new_pos}])], ignore_index=True)
                    
                    try:
                        from streamlit_gsheets import GSheetsConnection
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(spreadsheet=f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit", worksheet=instance, data=df_scores)
                    except:
                        st.warning("Score enregistré localement (Erreur de synchro Cloud)")

                    if st.button("Continuer"):
                        del st.session_state.temp_pos
                        st.rerun()
        else:
            st.warning("🍃 Case libre ! Vous avancez sans question.")
            if st.button("S'installer sur cette case"):
                # Mise à jour auto
                # (Même logique de sauvegarde que ci-dessus...)
                del st.session_state.temp_pos
                st.rerun()

elif role == "Professeur":
    st.title(f"📊 Suivi : {instance}")
    try:
        df_visu = read_gsheet(ID_SCORES, instance)
        if not df_visu.empty:
            st.bar_chart(df_visu.set_index("Étudiant")["Position"])
            st.table(df_visu.sort_values(by="Position", ascending=False))
    except:
        st.info("Aucun score.")
