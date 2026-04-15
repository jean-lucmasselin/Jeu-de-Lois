import streamlit as st
import pandas as pd
import random
import os
import time
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

# --- SYNC COURS ---
try:
    tabs = get_tab_names(ID_QUESTIONS)
    config_df = read_gsheet(ID_SCORES, "Config")
    instance_forcee = str(config_df.columns[0]).strip()
except:
    tabs, instance_forcee = ["Supervision"], "Supervision"

# --- SIDEBAR ---
st.sidebar.title("Configuration")
role = st.sidebar.radio("Rôle :", ["Etudiant", "Professeur"])
instance = st.sidebar.selectbox("Cours :", tabs, index=tabs.index(instance_forcee) if instance_forcee in tabs else 0) if role == "Professeur" else instance_forcee
nom_utilisateur = st.sidebar.text_input("Ton Nom :")

# --- SECTION PROFESSEUR ---
if role == "Professeur":
    st.title(f"👨‍🏫 Tableau de Bord : {instance}")
    
    # Système d'auto-refresh (toutes les 15 secondes)
    if st.sidebar.toggle("Actualisation automatique", value=True):
        time.sleep(15)
        st.rerun()

    c1, c2 = st.columns([3, 1])
    with c1:
        try:
            df_v = read_gsheet(ID_SCORES, instance)
            if not df_v.empty:
                df_v.columns = [str(c).strip() for c in df_v.columns]
                # Nettoyage et Tri
                df_v = df_v[["Etudiant", "Position", "Coups", "Réussites"]].sort_values(by=["Position", "Réussites"], ascending=False)
                
                # Graphique
                st.subheader("📊 Progression des élèves")
                st.bar_chart(df_v.set_index("Etudiant")["Position"])
                
                # Tableau propre
                st.subheader("🏆 Classement")
                st.table(df_v.reset_index(drop=True))
            else:
                st.info("En attente de joueurs...")
        except Exception as e: st.info(f"En attente de données... ({e})")
    
    with c2:
        if os.path.exists(NOM_FICHIER_QR): st.image(Image.open(NOM_FICHIER_QR), caption="Scanner pour jouer")

# --- SECTION ETUDIANT ---
elif role == "Etudiant":
    if not nom_utilisateur:
        st.info("👋 Entre ton nom à gauche pour commencer !")
    else:
        try:
            df_q = read_gsheet(ID_QUESTIONS, instance)
            df_q.columns = [str(c).strip() for c in df_q.columns]
            df_s = read_gsheet(ID_SCORES, instance)
            df_s.columns = [str(c).strip() for c in df_s.columns]
            
            # Récupération des stats
            user_data = df_s[df_s["Etudiant"] == nom_utilisateur]
            if not user_data.empty:
                curr_pos = int(user_data["Position"].values[0])
                curr_coups = int(user_data["Coups"].values[0])
                curr_reussites = int(user_data["Réussites"].values[0])
            else:
                curr_pos, curr_coups, curr_reussites = 0, 0, 0
            
            max_c = int(df_q['Case'].max())
        except:
            curr_pos, max_c, curr_coups, curr_reussites = 0, 20, 0, 0

        # --- GESTION DE LA VICTOIRE ---
        if curr_pos >= max_c:
            st.title("🎉 FÉLICITATIONS !")
            st.balloons()
            # Calcul du rang
            classement = df_s.sort_values(by=["Position", "Réussites"], ascending=False)["Etudiant"].tolist()
            rang = classement.index(nom_utilisateur) + 1 if nom_utilisateur in classement else "?"
            
            st.success(f"### Tu as terminé le parcours !")
            st.metric("Ton Rang", f"{rang}er" if rang == 1 else f"{rang}ème")
            st.write(f"Score final : **{curr_reussites}** bonnes réponses en **{curr_coups}** coups.")
            if st.button("Recommencer au début"):
                # Reset position uniquement
                try:
                    from streamlit_gsheets import GSheetsConnection
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_s.loc[df_s["Etudiant"] == nom_utilisateur, "Position"] = 0
                    conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=df_s)
                    st.rerun()
                except: pass
        
        else:
            st.title(f"📍 Parcours : {instance}")
            st.metric("Ma position", f"Case {curr_pos} / {max_c}")
            
            if 'temp_pos' not in st.session_state:
                if st.button("🎲 Lancer le dé"):
                    de = random.randint(1, 6)
                    st.session_state.temp_pos = min(curr_pos + de, max_c)
                    st.rerun()
            else:
                t_pos = st.session_state.temp_pos
                st.subheader(f"🚀 Tu vises la case : {t_pos}")
                q_data = df_q[df_q['Case'] == t_pos]
                
                if not q_data.empty:
                    q_row = q_data.iloc[0]
                    if 'rep_validee' not in st.session_state:
                        with st.form("quiz"):
                            st.write(f"**Question :** {q_row['Question']}")
                            choix = st.radio("Ta réponse :", [str(q_row['A']), str(q_row['B']), str(q_row['C'])])
                            if st.form_submit_button("Valider"):
                                m_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                                juste = (m_inv[choix] == str(q_row['Bonne']).strip().upper())
                                
                                # Calcul nouvelles stats
                                nouvelle_p = t_pos if juste else max(0, curr_pos - 1)
                                nouveau_coups = curr_coups + 1
                                nouvelle_reussite = curr_reussites + (1 if juste else 0)
                                
                                # SAUVEGARDE
                                try:
                                    from streamlit_gsheets import GSheetsConnection
                                    conn = st.connection("gsheets", type=GSheetsConnection)
                                    if nom_utilisateur in df_s["Etudiant"].values:
                                        df_s.loc[df_s["Etudiant"] == nom_utilisateur, ["Position", "Coups", "Réussites"]] = [nouvelle_p, nouveau_coups, nouvelle_reussite]
                                    else:
                                        df_s = pd.concat([df_s, pd.DataFrame([{"Etudiant": nom_utilisateur, "Position": nouvelle_p, "Coups": nouveau_coups, "Réussites": nouvelle_reussite}])], ignore_index=True)
                                    conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=df_s)
                                except: pass

                                st.session_state.rep_validee = True
                                st.session_state.res = (juste, str(q_row['Bonne']).strip().upper(), nouvelle_p)
                                st.rerun()
                    else:
                        j, b, p = st.session_state.res
                        if j: st.success("✨ BRAVO ! Bonne réponse.")
                        else: st.error(f"❌ DOMMAGE ! La réponse était {b}. Tu recules en case {p}.")
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
                            if nom_utilisateur in df_s["Etudiant"].values:
                                df_s.loc[df_s["Etudiant"] == nom_utilisateur, ["Position", "Coups"]] = [t_pos, curr_coups + 1]
                            else:
                                df_s = pd.concat([df_s, pd.DataFrame([{"Etudiant": nom_utilisateur, "Position": t_pos, "Coups": 1, "Réussites": 0}])], ignore_index=True)
                            conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=df_s)
                        except: pass
                        del st.session_state.temp_pos
                        st.rerun()
