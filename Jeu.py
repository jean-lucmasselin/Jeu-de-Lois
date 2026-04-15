import streamlit as st
import pandas as pd
import random
import os
import time
from datetime import datetime
from PIL import Image

st.set_page_config(page_title="Jeu de l'Oie Pédagogique", layout="wide")

# --- CONFIGURATION ---
ID_QUESTIONS = "1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E"
ID_SCORES = "1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc"
URL_SCORES = f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit"
NOM_FICHIER_QR = "QR code jeu de lois 2026.png" 

def read_gsheet(file_id, sheet_name):
    cb = random.randint(1, 99999)
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}&x={cb}"
    return pd.read_csv(url)

@st.cache_data(ttl=5)
def get_tab_names(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    return pd.ExcelFile(url).sheet_names

# --- SYNC DU COURS ACTIF (Lecture de l'onglet Config) ---
try:
    tabs = get_tab_names(ID_QUESTIONS)
    config_df = read_gsheet(ID_SCORES, "Config")
    # On lit le nom du cours stocké (en-tête de la colonne A)
    instance_active = str(config_df.columns[0]).strip()
except:
    tabs, instance_active = ["Supervision"], "Supervision"

# --- SIDEBAR (Navigateur) ---
st.sidebar.title("🎲 Configuration")
role = st.sidebar.radio("Mon Rôle :", ["Étudiant", "Professeur"])

if role == "Professeur":
    # Sélection du cours
    nouveau_cours = st.sidebar.selectbox("Choisir le cours :", tabs, index=tabs.index(instance_active) if instance_active in tabs else 0)
    
    # Bouton de validation pour toute la classe
    if st.sidebar.button("✅ Valider pour toute la classe"):
        try:
            from streamlit_gsheets import GSheetsConnection
            conn = st.connection("gsheets", type=GSheetsConnection)
            # On écrit le nom du cours dans l'onglet Config
            df_config = pd.DataFrame(columns=[nouveau_cours])
            conn.update(spreadsheet=URL_SCORES, worksheet="Config", data=df_config)
            st.sidebar.success(f"Cours '{nouveau_cours}' activé !")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Erreur Config : {e}")
    
    instance = nouveau_cours # Le prof travaille sur ce qu'il a sélectionné
else:
    # L'étudiant subit le cours choisi par le prof (bandeau vert)
    instance = instance_active
    st.sidebar.success(f"Cours actif : **{instance}**")

nom_utilisateur = st.sidebar.text_input("Votre Nom :")

# --- SECTION PROFESSEUR ---
if role == "Professeur":
    st.title(f"👨‍🏫 Tableau de Bord : {instance}")
    
    if st.sidebar.toggle("Actualisation automatique", value=True):
        time.sleep(15)
        st.rerun()

    c1, c2 = st.columns([3, 1])
    with c1:
        try:
            df_v = read_gsheet(ID_SCORES, instance)
            if not df_v.empty:
                df_v.columns = [str(c).strip() for c in df_v.columns]
                # On ne garde que les colonnes utiles pour éviter les doublons
                df_v = df_v[["Etudiant", "Position", "Coups", "Réussites", "Date", "Debut", "Fin"]]
                df_v = df_v.sort_values(by=["Position", "Réussites"], ascending=False)
                
                st.subheader("📊 Progression")
                st.bar_chart(df_v.set_index("Etudiant")["Position"])
                
                st.subheader("🏆 Résultats détaillés")
                st.table(df_v.reset_index(drop=True))
            else:
                st.info("En attente de joueurs...")
        except: st.info("Aucune donnée disponible.")
    
    with c2:
        st.subheader("QR Code")
        if os.path.exists(NOM_FICHIER_QR):
            st.image(Image.open(NOM_FICHIER_QR), use_container_width=True)
        else:
            st.warning("QR Code absent sur GitHub")

# --- SECTION ÉTUDIANT ---
elif role == "Étudiant":
    if not nom_utilisateur:
        st.info("👋 Bienvenue ! Entrez votre nom à gauche pour commencer.")
    else:
        try:
            df_q = read_gsheet(ID_QUESTIONS, instance)
            df_q.columns = [str(c).strip() for c in df_q.columns]
            df_s = read_gsheet(ID_SCORES, instance)
            df_s.columns = [str(c).strip() for c in df_s.columns]
            
            user_data = df_s[df_s["Etudiant"] == nom_utilisateur]
            if not user_data.empty:
                curr_pos = int(user_data["Position"].values[0])
                curr_coups = int(user_data["Coups"].values[0])
                curr_reussites = int(user_data["Réussites"].values[0])
                start_time = str(user_data["Debut"].values[0])
            else:
                curr_pos, curr_coups, curr_reussites = 0, 0, 0
                start_time = None
            
            max_c = int(df_q['Case'].max())
        except:
            curr_pos, max_c, curr_coups, curr_reussites, start_time = 0, 20, 0, 0, None

        # --- VICTOIRE ---
        if curr_pos >= max_c:
            st.title("🎉 ARRIVÉE !")
            st.balloons()
            st.success(f"### Félicitations {nom_utilisateur} !")
            st.write(f"Tu as terminé avec **{curr_reussites}** réussites en **{curr_coups}** coups.")
            if st.button("Recommencer au début"):
                # Reset
                st.rerun()
        
        else:
            st.title(f"📍 Parcours : {instance}")
            st.metric("Ma position", f"Case {curr_pos} / {max_c}")
            
            if 'temp_pos' not in st.session_state:
                if st.button("🎲 Lancer le dé"):
                    de = random.randint(1, 6)
                    st.session_state.temp_pos = min(curr_pos + de, max_c)
                    # Heure de début au premier lancer
                    if not start_time or start_time == "nan":
                        st.session_state.start_time = datetime.now().strftime("%H:%M:%S")
                    else:
                        st.session_state.start_time = start_time
                    st.rerun()
            else:
                t_pos = st.session_state.temp_pos
                st.subheader(f"🚀 Case visée : {t_pos}")
                q_data = df_q[df_q['Case'] == t_pos]
                
                if not q_data.empty:
                    q_row = q_data.iloc[0]
                    if 'rep_validee' not in st.session_state:
                        with st.form("quiz"):
                            st.write(f"**Question :** {q_row['Question']}")
                            choix = st.radio("Réponse :", [str(q_row['A']), str(q_row['B']), str(q_row['C'])])
                            if st.form_submit_button("Valider"):
                                m_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                                juste = (m_inv[choix] == str(q_row['Bonne']).strip().upper())
                                
                                # Stats
                                n_pos = t_pos if juste else max(0, curr_pos - 1)
                                n_coups = curr_coups + 1
                                n_reuss = curr_reussites + (1 if juste else 0)
                                now = datetime.now()
                                
                                # Sauvegarde
                                try:
                                    from streamlit_gsheets import GSheetsConnection
                                    conn = st.connection("gsheets", type=GSheetsConnection)
                                    data_up = {
                                        "Etudiant": nom_utilisateur,
                                        "Position": n_pos,
                                        "Coups": n_coups,
                                        "Réussites": n_reuss,
                                        "Date": now.strftime("%d/%m/%Y"),
                                        "Debut": st.session_state.start_time,
                                        "Fin": now.strftime("%H:%M:%S")
                                    }
                                    if nom_utilisateur in df_s["Etudiant"].values:
                                        df_s.loc[df_s["Etudiant"] == nom_utilisateur, ["Position", "Coups", "Réussites", "Date", "Debut", "Fin"]] = [n_pos, n_coups, n_reuss, data_up["Date"], data_up["Debut"], data_up["Fin"]]
                                    else:
                                        df_s = pd.concat([df_s, pd.DataFrame([data_up])], ignore_index=True)
                                    conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=df_s)
                                except: pass

                                st.session_state.rep_validee = True
                                st.session_state.res = (juste, str(q_row['Bonne']).strip().upper(), n_pos)
                                st.rerun()
                    else:
                        j, b, p = st.session_state.res
                        if j: st.success("✨ Bonne réponse !")
                        else: st.error(f"❌ Mauvaise réponse (c'était {b}). Retour en case {p}.")
                        if st.button("Continuer"):
                            del st.session_state.temp_pos
                            del st.session_state.rep_validee
                            st.rerun()
                else:
                    st.warning("🍃 Case libre !")
                    if st.button("S'installer ici"):
                        try:
                            from streamlit_gsheets import GSheetsConnection
                            conn = st.connection("gsheets", type=GSheetsConnection)
                            now = datetime.now()
                            # Heure de début si c'est la première action
                            s_t = st.session_state.get('start_time', now.strftime("%H:%M:%S"))
                            
                            if nom_utilisateur in df_s["Etudiant"].values:
                                df_s.loc[df_s["Etudiant"] == nom_utilisateur, ["Position", "Coups", "Date", "Fin"]] = [t_pos, curr_coups + 1, now.strftime("%d/%m/%Y"), now.strftime("%H:%M:%S")]
                            else:
                                nl = {"Etudiant": nom_utilisateur, "Position": t_pos, "Coups": 1, "Réussites": 0, "Date": now.strftime("%d/%m/%Y"), "Debut": s_t, "Fin": now.strftime("%H:%M:%S")}
                                df_s = pd.concat([df_s, pd.DataFrame([nl])], ignore_index=True)
                            conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=df_s)
                        except: pass
                        del st.session_state.temp_pos
                        st.rerun()
