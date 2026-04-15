import streamlit as st
import pandas as pd
import random
import os

st.set_page_config(page_title="Jeu de l'Oie Pédagogique", layout="wide")

# --- BLOQUE DE TEST - À SUPPRIMER UNE FOIS qr_code.png SUR GITHUB ---
if not os.path.exists("qr_code.png"):
    # Crée une image de test vide si qr_code.png n'existe pas encore
    from PIL import Image
    test_img = Image.new('RGB', (100, 100), color = (73, 109, 137))
    test_img.save("qr_code.png")
# ----------------------------------------------------------------------

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

# --- AFFICHAGE AU DÉMARRAGE (QUAND LE NAVIGATEUR EST FERMÉ SUR SMARTPHONE) ---
# Seuls les étudiants voient ce message
if role == "Étudiant" and not nom_utilisateur:
    with st.container(border=True):
        st.subheader("👋 Bienvenue sur le Jeu de l'Oie !")
        st.info("👈 Pour commencer à jouer, merci d'ouvrir le menu (en haut à gauche) et d'y entrer votre nom.")
        st.stop() # On s'arrête là tant que le nom n'est pas rempli

# --- CHARGEMENT ---
try:
    df_questions = read_gsheet(ID_QUESTIONS, instance)
    df_questions.columns = [str(c).strip() for c in df_questions.columns]
    
    if 'Case' not in df_questions.columns:
        st.error(f"La colonne 'Case' est absente de l'onglet {instance}.")
        st.stop()
        
    MAX_CASES = int(df_questions['Case'].max())
except Exception as e:
    # Message de repli pour l'étudiant si la connexion Google est en attente
    if role == "Étudiant":
        with st.container(border=True):
            st.subheader(f"📍 Instance : {instance}")
            st.info("Attendez le lancement du jeu...")
    else:
        st.sidebar.error(f"Erreur de chargement : {e}")
    st.stop()

# --- LOGIQUE ÉTUDIANT ---
if role == "Étudiant":
    st.title(f"📍 Parcours : {instance}")
    
    # Récupération Position
    try:
        df_scores = read_gsheet(ID_SCORES, instance)
        df_scores.columns = [str(c).strip() for c in df_scores.columns]
        current_pos = int(df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"].values[0]) if nom_utilisateur in df_scores["Étudiant"].values else 0
    except:
        df_scores = pd.DataFrame(columns=["Étudiant", "Position"])
        current_pos = 0

    st.metric("Ma position actuelle", f"Case {current_pos} / {MAX_CASES}")

    # 1. BOUTON LANCER LE DÉ
    if 'temp_pos' not in st.session_state:
        if st.button("🎲 Lancer le dé pour progresser"):
            de = random.randint(1, 6)
            st.session_state.temp_pos = min(current_pos + de, MAX_CASES)
            st.session_state.show_form = True # Drapeau pour afficher le formulaire
            st.rerun()
    # 2. GESTION DE LA QUESTION
    else:
        pos = st.session_state.temp_pos
        st.subheader(f"🚀 Case visée : {pos}")

        question_data = df_questions[df_questions['Case'] == pos]
        
        if not question_data.empty:
            q_row = question_data.iloc[0]
            
            # Formulaire de réponse (si pas validé)
            if st.session_state.get('show_form', True):
                with st.form("quiz_form"):
                    st.write(f"**Question :** {q_row['Question']}")
                    options = [str(q_row['A']), str(q_row['B']), str(q_row['C'])]
                    choix = st.radio("Votre réponse :", options)
                    submit_button = st.form_submit_button("Valider la réponse")
                    
                    if submit_button:
                        st.session_state.choix_utilisateur = choix
                        st.session_state.show_form = False # On cache le formulaire
                        st.rerun() # Rafraîchir pour afficher le résultat

            # --- AFFICHAGE DU RÉSULTAT (VERT OU ROUGE) ---
            if 'choix_utilisateur' in st.session_state:
                choix_form = st.session_state.choix_utilisateur
                map_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                bonne_rep_lettre = str(q_row['Bonne']).strip().upper()
                
                # Bilan
                juste = (map_inv[choix_form] == bonne_rep_lettre)
                
                # MISE À JOUR & SAUVEGARDE
                if juste:
                    # ✅ VERT - Bonne réponse
                    new_pos = pos
                    #st.success(f"✨ Bravo {nom_utilisateur} ! Bonne réponse.")
                else:
                    # ❌ ROUGE - Mauvaise réponse
                    new_pos = max(0, current_pos - 1)
                    #st.error(f"❌ Dommage ! La bonne réponse était la **{bonne_rep_lettre}**. Vous reculez d'une case (case {new_pos}).")
                
                # Mise à jour sur Google Sheet
                if nom_utilisateur in df_scores["Étudiant"].values:
                    df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = new_pos
                else:
                    new_line = pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": new_pos}])
                    df_scores = pd.concat([df_scores, new_line], ignore_index=True)
                
                try:
                    from streamlit_gsheets import GSheetsConnection
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(spreadsheet=f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit", worksheet=instance, data=df_scores)
                except:
                    pass # Erreur silencieuse d'écriture

                # --- AFFICHAGE DES BANDEAUX & BOUTON CONTINUER ---
                if juste:
                    st.success(f"✨ Bravo {nom_utilisateur} ! Bonne réponse.")
                else:
                    st.error(f"❌ Dommage ! La bonne réponse était la **{bonne_rep_lettre}**. Vous reculez d'une case (case {new_pos}).")

                # BOUTON POUR RELANCER (Remet tout à zéro)
                if st.button("Continuer (jeter à nouveau les dés)"):
                    # Nettoyage de la session pour un nouveau tour
                    del st.session_state.temp_pos
                    del st.session_state.choix_utilisateur
                    if 'show_form' in st.session_state: del st.session_state.show_form
                    st.rerun()

        else:
            # CAS OÙ LA CASE N'A PAS DE QUESTION
            st.warning("🍃 Case libre ! Vous avancez sans question.")
            if st.button("Prendre position sur cette case"):
                if nom_utilisateur in df_scores["Étudiant"].values:
                    df_scores.loc[df_scores["Étudiant"] == nom_utilisateur, "Position"] = pos
                else:
                    new_line = pd.DataFrame([{"Étudiant": nom_utilisateur, "Position": pos}])
                    df_scores = pd.concat([df_scores, new_line], ignore_index=True)
                
                from streamlit_gsheets import GSheetsConnection
                conn = st.connection("gsheets", type=GSheetsConnection)
                conn.update(spreadsheet=f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit", worksheet=instance, data=df_scores)
                del st.session_state.temp_pos
                st.rerun()

elif role == "Professeur":
    st.title(f"👨‍🏫 Tableau de Bord : {instance}")
    
    # Colonne pour le QR Code et Suivi
    col_suivi, col_qr = st.columns([3, 1])
    
    with col_suivi:
        st.subheader("Suivi de progression")
        try:
            df_visu = read_gsheet(ID_SCORES, instance)
            if not df_visu.empty:
                st.bar_chart(df_visu.set_index("Étudiant")["Position"])
                st.table(df_visu.sort_values(by="Position", ascending=False))
            else:
                st.info("Aucun score enregistré.")
        except:
            st.info("Aucun score enregistré.")

    with col_qr:
        st.subheader("Connexion Étudiants")
        # Affichage du QR Code (Fichier PNG)
        if os.path.exists("qr_code.png"):
            from PIL import Image
            qr_code_img = Image.open("qr_code.png")
            # Affichage de l'image (responsif)
            st.image(qr_code_img, caption="Scanner pour rejoindre le jeu", use_column_width=True)
        else:
            st.warning("QR Code absent (placez qr_code.png sur GitHub).")
