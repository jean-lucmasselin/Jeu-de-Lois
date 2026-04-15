import streamlit as st
import pandas as pd
import random
import os
from PIL import Image

st.set_page_config(page_title="Jeu de l'Oie Pédagogique", layout="wide")

# --- CONFIGURATION ---
ID_QUESTIONS = "1-8CSR3Qd83t1VoJb4ppfBXRRmxPeE_EcBva19mlqY9E"
ID_SCORES = "1-kIkRy_krSDRA77bb1kQVPGBA166VQ6OsL8G3GIzKgc"
URL_SCORES = f"https://docs.google.com/spreadsheets/d/{ID_SCORES}/edit"
NOM_FICHIER_QR = "qr_code.png" 

def read_gsheet(file_id, sheet_name):
    cb = random.randint(1, 99999)
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}&x={cb}"
    return pd.read_csv(url)

@st.cache_data(ttl=5)
def get_tab_names(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    return pd.ExcelFile(url).sheet_names

# --- GESTION DU COURS ACTIF ---
try:
    tabs = get_tab_names(ID_QUESTIONS)
    config_df = read_gsheet(ID_SCORES, "Config")
    instance_forcee = str(config_df.columns[0]).strip()
except:
    tabs = ["Supervision"] 
    instance_forcee = "Supervision"

# --- INTERFACE LATERALE ---
st.sidebar.title("Configuration")
role = st.sidebar.radio("Mon Role :", ["Etudiant", "Professeur"])

if role == "Professeur":
    instance = st.sidebar.selectbox("Cours :", tabs, index=tabs.index(instance_forcee) if instance_forcee in tabs else 0)
    st.session_state['active_instance'] = instance
else:
    instance = instance_forcee
    st.sidebar.success(f"Cours : {instance}")

nom_utilisateur = st.sidebar.text_input("Ton Nom :")

# --- SECTION PROFESSEUR ---
if role == "Professeur":
    st.title(f"Tableau de Bord : {instance}")
    col_g, col_d = st.columns([3, 1])
    with col_g:
        try:
            df_v = read_gsheet(ID_SCORES, instance)
            if not df_v.empty:
                df_v.columns = [str(c).strip() for c in df_v.columns]
                st.bar_chart(df_v.set_index("Etudiant")["Position"])
                st.table(df_v.sort_values(by="Position", ascending=False))
            else:
                st.info("En attente de joueurs...")
        except:
            st.info("Aucun score enregistre.")
    with col_d:
        if os.path.exists(NOM_FICHIER_QR):
            st.image(Image.open(NOM_FICHIER_QR), use_container_width=True)

# --- SECTION ETUDIANT ---
elif role == "Etudiant":
    if not nom_utilisateur:
        st.info("Bienvenue ! Entre ton nom a gauche pour jouer.")
    else:
        st.title(f"Parcours : {instance}")
        try:
            df_q = read_gsheet(ID_QUESTIONS, instance)
            df_q.columns = [str(c).strip() for c in df_q.columns]
            df_s = read_gsheet(ID_SCORES, instance)
            df_s.columns = [str(c).strip() for c in df_s.columns]
            
            curr_pos = int(df_s.loc[df_s["Etudiant"] == nom_utilisateur, "Position"].values[0]) if nom_utilisateur in df_s["Etudiant"].values else 0
            max_c = int(df_q['Case'].max())
        except:
            curr_pos = 0
            max_c = 20

        st.metric("Ma position", f"Case {curr_pos} / {max_c}")

        if 'temp_pos' not in st.session_state:
            if st.button("Lancer le de"):
                de = random.randint(1, 6)
                st.session_state.temp_pos = min(curr_pos + de, max_c)
                st.rerun()
        else:
            t_pos = st.session_state.temp_pos
            st.subheader(f"Case visee : {t_pos}")
            try:
                q_row = df_q[df_q['Case'] == t_pos].iloc[0]
                if 'rep_validee' not in st.session_state:
                    with st.form("form_q"):
                        st.write(f"Question : {q_row['Question']}")
                        choix = st.radio("Ta reponse :", [str(q_row['A']), str(q_row['B']), str(q_row['C'])])
                        if st.form_submit_button("Valider"):
                            m_inv = {str(q_row['A']): 'A', str(q_row['B']): 'B', str(q_row['C']): 'C'}
                            bonne = str(q_row['Bonne']).strip().upper()
                            juste = (m_inv[choix] == bonne)
                            nouvelle_p = t_pos if juste else max(0, curr_pos - 1)
                            
                            # SAUVEGARDE
                            try:
                                from streamlit_gsheets import GSheetsConnection
                                conn = st.connection("gsheets", type=GSheetsConnection)
                                if not df_s.empty and nom_utilisateur in df_s["Etudiant"].values:
                                    df_s.loc[df_s["Etudiant"] == nom_utilisateur, "Position"] = nouvelle_p
                                else:
                                    nl = pd.DataFrame([{"Etudiant": nom_utilisateur, "Position": nouvelle_p}])
                                    df_s = pd.concat([df_s, nl], ignore_index=True)
                                # MISE À JOUR DU FICHIER
                                conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=df_s)
                            except Exception as e:
                                st.error(f"Erreur d'ecriture Google : {e}")

                            st.session_state.rep_validee = True
                            st.session_state.msg_res = (juste, bonne, nouvelle_p)
                            st.rerun()
                
                if st.session_state.get('rep_validee'):
                    j, b, p = st.session_state.msg_res
                    if j: st.success("Bravo ! Bonne reponse.")
                    else: st.error(f"Dommage ! La reponse etait {b}. Tu recules en case {p}.")
                    if st.button("Continuer"):
                        del st.session_state.temp_pos
                        del st.session_state.rep_validee
                        st.rerun()
            except:
                st.warning("Case libre !")
                if st.button("S'installer ici"):
                    # Code de sauvegarde pour case libre
                    try:
                        from streamlit_gsheets import GSheetsConnection
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        if not df_s.empty and nom_utilisateur in df_s["Etudiant"].values:
                            df_s.loc[df_s["Etudiant"] == nom_utilisateur, "Position"] = t_pos
                        else:
                            nl = pd.DataFrame([{"Etudiant": nom_utilisateur, "Position": t_pos}])
                            df_s = pd.concat([df_s, nl], ignore_index=True)
                        conn.update(spreadsheet=URL_SCORES, worksheet=instance, data=df_s)
                    except: pass
                    del st.session_state.temp_pos
                    st.rerun()
