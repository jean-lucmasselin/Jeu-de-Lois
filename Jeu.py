import streamlit as st
import pandas as pd
import random
import os
from PIL import Image

st.set_page_config(page_title="Jeu de l'Oie Pédagogique", layout="wide")

# --- CONFIGURATION ---
ID_QUESTIONS = "1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E"
ID_SCORES = "1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc"
NOM_FICHIER_QR = "qr_code.png"

def read_gsheet(file_id, sheet_name):
    # On ajoute un nombre aléatoire à l'URL pour forcer Google à donner la version la plus récente
    cache_bust = random.randint(1, 100000)
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}&x={cache_bust}"
    return pd.read_csv(url)

@st.cache_data(ttl=10) # Cache très court pour voir les changements de cours
def get_tab_names(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    return pd.ExcelFile(url).sheet_names

# --- GESTION DU COURS ACTIF (SYNCHRONISATION) ---
tabs = get_tab_names(ID_QUESTIONS)

# Par défaut, on cherche si le prof a défini un cours dans l'onglet "Config" du fichier Score
# Si l'onglet n'existe pas, on prend le premier de la liste
try:
    config_df = read_gsheet(ID_SCORES, "Config")
    instance_forcee = str(config_df.columns[0]).strip()
except:
    instance_forcee = tabs[0]

# --- INTERFACE LATÉRALE ---
st.sidebar.title("🎲 Configuration")
role = st.sidebar.radio("Mon Rôle :", ["Étudiant", "Professeur"])

if role == "Professeur":
    instance = st.sidebar.selectbox("Choisir le cours pour TOUS :", tabs, index=tabs.index(instance_forcee) if instance_forcee in tabs else 0)
    if st.sidebar.button("💾 Valider ce cours pour la classe"):
        st.sidebar.warning("Pour synchroniser, assurez-vous d'avoir un onglet 'Config' dans votre Sheet Score.")
else:
    instance = instance_forcee
    st.sidebar.success(f"Cours actif : **{instance}**")

nom_utilisateur = st.sidebar.text_input("Votre Nom :")

# --- ACCUEIL ÉTUDIANT ---
if role == "Étudiant" and not nom_utilisateur:
    st.info("👋 **Bienvenue !** Entrez votre nom dans le menu à gauche pour rejoindre la partie.")
    st.stop()

# --- CHARGEMENT DES QUESTIONS ---
try:
    df_questions = read_gsheet(ID_QUESTIONS, instance)
    df_questions.columns = [str(c).strip() for c in df_questions.columns]
    MAX_CASES = int(df_questions['Case'].max())
except:
    st.error(f"Erreur : Impossible de charger l'onglet '{instance}'.")
    st.stop()

# --- LOGIQUE ÉTUDIANT ---
if role == "Étudiant":
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
        if st.button("🎲 Lancer le dé"):
            de = random.randint(1, 6)
            st.session_state.temp_pos = min(current_pos + de, MAX_CASES)
            st.rerun()
    else:
        pos = st.session_state.temp_pos
        st.subheader(f"🚀 Case visée : {pos}")
        q_data = df_questions[df_questions['Case'] == pos]
        
        if not q_data.empty:
            q_row = q_data.iloc[0]
            if 'reponse_validee' not in st.session_state:
                with st.form("quiz"):
                    st.write(f"**Question :** {q_row['Question']}")
                    choix = st.radio("Réponse :", [str(q_row['A']), str(q_row['B']), str(q_row['C'])])
                    if st.form_submit_button("Valider"):
                        map_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                        bonne_rep = str(q_row['Bonne']).strip().upper()
                        juste = (map_inv[choix] == bonne_rep)
                        new_pos = pos if juste else max(0, current_pos - 1)
                        
                        # --- SAUVEGARDE VIA GSPREAD (Connexion simplifiée) ---
                        try:
                            from streamlit_gsheets import GSheetsConnection
                            conn = st.connection("gsheets", type=GSheetsConnection)
                            
                            if nom_utilisateur in df_scores["Étudiant"].values:
                                df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = new_pos
                            else:
                                df_scores = pd.concat([df_scores, pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": new_pos}])], ignore_index=True)
                            
                            # On utilise une méthode plus simple pour l'écriture
                            conn.update(spreadsheet=f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit", worksheet=instance, data=df_scores)
                        except Exception as e:
                            st.error(f"Erreur d'enregistrement. Vérifiez que l'onglet '{instance}' existe dans le fichier SCORE et que vous avez configuré les Secrets Streamlit.")
                        
                        st.session_state.reponse_validee = True
                        st.session_state.res_msg = (juste, bonne_rep, new_pos)
                        st.rerun()

            if st.session_state.get('reponse_validee'):
                juste, bonne_rep, new_pos = st.session_state.res_msg
                if juste: st.success("✨ Bravo ! Bonne réponse.")
                else: st.error(f"❌ Dommage ! La réponse était {bonne_rep}. Vous reculez en case {new_pos}.")
                
                if st.button("Continuer"):
                    del st.session_state.temp_pos
                    del st.session_state.reponse_validee
                    st.rerun()
        else:
            st.warning("Case libre !")
            if st.button("S'installer ici"):
                del st.session_state.temp_pos
                st.rerun()

elif role == "Professeur":
    st.title(f"👨‍🏫 Tableau de Bord : {instance}")
    c1, c2 = st.columns([3, 1])
    with c1:
        try:
            df_v = read_gsheet(ID_SCORES, instance)
            if not df_v.empty:
                st.bar_chart(df_v.set_index("Étudiant")["Position"])
                st.table(df_v.sort_values(by="Position", ascending=False))
        except: st.info("En attente...")
    with c2:
        if os.path.exists(NOM_FICHIER_QR): st.image(Image.open(NOM_FICHIER_QR))
