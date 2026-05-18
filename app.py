"""
app.py - Salary Management System (State Administration)
Main Streamlit application entry point.
Features: Employee CRUD, Grade/Echelon management, Salary calculation,
Payroll processing, Payslip generation, Import/Export, Dashboard.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from io import BytesIO, StringIO

import database as db
import salary_engine as se
from auth import (
    init_session_state, login_page, nav_sidebar,
    require_auth, is_admin, get_current_user_id, logout
)
from payslip import generate_payslip_html, generate_payslip_summary_card

# ─────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="State Salary Management",
    page_icon="🏛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
if "db_initialized" not in st.session_state:
    db.init_database()
    st.session_state.db_initialized = True

init_session_state()


# ═════════════════════════════════════════
# PAGE: Dashboard (Admin)
# ═════════════════════════════════════════
def render_dashboard():
    st.markdown("""
        <h1 style="color: #2C3E50;">🏛 Tableau de Bord - Gestion des Salaires</h1>
        <p style="color: #7F8C8D; font-size: 1.1em;">Ministere des Finances - Administration de l'Etat</p>
        <hr style="border: 1px solid #BDC3C7;">
    """, unsafe_allow_html=True)

    # Key metrics
    stats = db.get_dashboard_stats()
    monthly = db.get_monthly_payroll_totals()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("👥 Employes Actifs", stats["total_active"], delta=None)
    with c2:
        st.metric("📋 Total Employes", stats["total_employees"])
    with c3:
        st.metric("⏳ Paies en Attente", stats["pending_payrolls"])
    with c4:
        st.metric("💰 Total Traite", f"{stats['total_processed']:,.0f} DA")
    with c5:
        st.metric("📅 Mois Traités", stats["total_months"])

    st.markdown("<hr>", unsafe_allow_html=True)

    # Charts row
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 Evolution du Cumul Salarial")
        if monthly:
            df_monthly = pd.DataFrame(monthly)
            df_monthly["mois_label"] = pd.to_datetime(df_monthly["mois"]).dt.strftime("%b %Y")
            df_monthly = df_monthly.sort_values("mois")

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_monthly["mois_label"], y=df_monthly["total_brut"],
                name="Salaire Brut", line=dict(color="#3498DB", width=3),
                fill="tozeroy", fillcolor="rgba(52,152,219,0.1)"
            ))
            fig.add_trace(go.Scatter(
                x=df_monthly["mois_label"], y=df_monthly["total_net"],
                name="Salaire Net", line=dict(color="#27AE60", width=3),
                fill="tozeroy", fillcolor="rgba(39,174,96,0.1)"
            ))
            fig.update_layout(
                xaxis_title="Mois", yaxis_title="Montant (DA)",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=40, t=40, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnee de paie disponible. Traitez une paie mensuelle pour voir les statistiques.")

    with col_right:
        st.subheader("📈 Repartition Salaire par Categorie")
        employes = db.get_all_employes()
        if employes:
            df_emp = pd.DataFrame(employes)
            grade_counts = df_emp["code_grade"].value_counts()
            fig = px.pie(
                names=grade_counts.index, values=grade_counts.values,
                color_discrete_sequence=px.colors.sequential.Blues_r,
                hole=0.4
            )
            fig.update_traces(textinfo="label+percent", textfont_size=12)
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=40, t=40, b=40), showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucun employe enregistre.")

    # Latest payrolls
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("📝 Dernieres Paies Traitees")
    if monthly:
        latest = monthly[:6]
        for lp in latest:
            mois_label = datetime.strptime(lp["mois"], "%Y-%m-%d").strftime("%B %Y").capitalize()
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
            with c1:
                st.write(f"**{mois_label}**")
            with c2:
                st.write(f"{lp['nb_employes']} employes")
            with c3:
                st.write(f"Brut: {lp['total_brut']:,.0f} DA")
            with c4:
                st.write(f"Net: {lp['total_net']:,.0f} DA")
            with c5:
                if st.button("Details", key=f"dash_btn_{lp['mois']}"):
                    st.session_state.view_month = lp["mois"]
                    st.session_state.page = "payslips"
                    st.rerun()
    else:
        st.info("Aucune paie n'a encore ete traitee.")


# ═════════════════════════════════════════
# PAGE: Employees (Admin)
# ═════════════════════════════════════════
def render_employees():
    st.markdown("""
        <h1 style="color: #2C3E50;">👥 Gestion des Employes</h1>
        <p style="color: #7F8C8D;">CRUD Complet du Personnel Administratif</p>
        <hr style="border: 1px solid #BDC3C7;">
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 Liste des Employes", "➕ Ajouter un Employe", "✏ Modifier / Supprimer"])

    # ── Tab 1: List ──
    with tab1:
        employes = db.get_all_employes()
        if employes:
            df = pd.DataFrame(employes)
            col_config = {
                "id_employe": st.column_config.NumberColumn("ID", width="small"),
                "nom": st.column_config.TextColumn("Nom Complet", width="medium"),
                "poste": st.column_config.TextColumn("Poste", width="medium"),
                "code_grade": st.column_config.TextColumn("Grade", width="small"),
                "numero_echelon": st.column_config.NumberColumn("Echelon", width="small"),
                "date_embauche": st.column_config.TextColumn("Date Embauche", width="medium"),
                "statut": st.column_config.TextColumn("Statut", width="small"),
                "salaire_base": st.column_config.NumberColumn("Salaire Base", format="%.2f DA"),
            }
            display_cols = [c for c in col_config.keys() if c in df.columns]
            st.dataframe(df[display_cols], column_config=col_config, use_container_width=True, hide_index=True)
            st.caption(f"Total: {len(employes)} employes")
        else:
            st.info("Aucun employe enregistre. Ajoutez des employes via l'onglet 'Ajouter'.")

    # ── Tab 2: Add ──
    with tab2:
        with st.form("add_employee_form", clear_on_submit=True):
            st.subheader("Nouvel Employe")
            nom = st.text_input("Nom et Prenom *", placeholder="Ex: Ahmed Benali")

            c1, c2 = st.columns(2)
            with c1:
                date_emb = st.date_input("Date d'embauche *", value=date(2020, 1, 1))
            with c2:
                nb_enfants = st.number_input("Nombre d'enfants", min_value=0, max_value=20, value=0)

            poste = st.text_input("Poste / Fonction", placeholder="Ex: Comptable")
            compte_banc = st.text_input("Compte Bancaire", placeholder="Ex: 00799999000012345678")

            grades = db.get_all_grades()
            echelons = db.get_all_echelons()

            c3, c4 = st.columns(2)
            with c3:
                grade_options = {g["code_grade"]: f"{g['code_grade']} (Base: {g['salaire_base']:,.0f} DA)" for g in grades}
                sel_grade = st.selectbox("Grade *", options=list(grade_options.keys()),
                                          format_func=lambda x: grade_options[x])
            with c4:
                ech_options = {e["id_echelon"]: f"Echelon {e['numero_echelon']}" for e in echelons}
                sel_echelon = st.selectbox("Echelon *", options=list(ech_options.keys()),
                                            format_func=lambda x: ech_options[x])

            statut = st.selectbox("Statut", ["actif", "en_conge", "retraite", "licencie"])

            submitted = st.form_submit_button("✅ Enregistrer l'Employe", use_container_width=True)
            if submitted:
                if not nom:
                    st.error("Le nom est obligatoire.")
                else:
                    emp_id = db.create_employe(
                        nom, str(date_emb), compte_banc or "",
                        poste or "", statut, nb_enfants, sel_grade, sel_echelon
                    )
                    st.success(f"Employe ajoute avec succes! ID: {emp_id}")
                    st.rerun()

    # ── Tab 3: Edit / Delete ──
    with tab3:
        employes = db.get_all_employes()
        if not employes:
            st.info("Aucun employe a modifier.")
            return

        emp_options = {e["id_employe"]: f"{e['id_employe']} - {e['nom']} ({e['code_grade']})" for e in employes}
        sel_id = st.selectbox("Selectionner un employe", options=list(emp_options.keys()),
                               format_func=lambda x: emp_options[x])

        emp = db.get_employe_by_id(sel_id)
        if not emp:
            st.error("Employe non trouve.")
            return

        with st.form("edit_employee_form"):
            edit_nom = st.text_input("Nom", value=emp["nom"])
            c1, c2 = st.columns(2)
            with c1:
                edit_poste = st.text_input("Poste", value=emp.get("poste", "") or "")
            with c2:
                edit_statut = st.selectbox("Statut", ["actif", "en_conge", "retraite", "licencie"],
                                            index=["actif", "en_conge", "retraite", "licencie"].index(emp["statut"]))

            c3, c4 = st.columns(2)
            with c3:
                edit_grade = st.selectbox("Grade", options=[g["code_grade"] for g in db.get_all_grades()],
                                           index=[g["code_grade"] for g in db.get_all_grades()].index(emp["code_grade"]))
            with c4:
                ech_list = db.get_all_echelons()
                edit_echelon = st.selectbox("Echelon", options=[e["id_echelon"] for e in ech_list],
                                             index=[e["id_echelon"] for e in ech_list].index(emp["id_echelon"]))

            edit_nb_enf = st.number_input("Nombre d'enfants", min_value=0, max_value=20,
                                           value=emp.get("nombre_enfants", 0) or 0)

            c_save, c_del = st.columns(2)
            with c_save:
                save_btn = st.form_submit_button("💾 Sauvegarder", use_container_width=True)
            with c_del:
                del_btn = st.form_submit_button("🗑 Supprimer", use_container_width=True, type="secondary")

            if save_btn:
                db.update_employe(sel_id, nom=edit_nom, poste=edit_poste, statut=edit_statut,
                                  code_grade=edit_grade, id_echelon=edit_echelon,
                                  nombre_enfants=edit_nb_enf)
                st.success("Modifications sauvegardees!")
                st.rerun()
            if del_btn:
                db.delete_employe(sel_id)
                st.success("Employe supprime!")
                st.rerun()


# ═════════════════════════════════════════
# PAGE: Grades & Echelons (Admin)
# ═════════════════════════════════════════
def render_grades():
    st.markdown("""
        <h1 style="color: #2C3E50;">📋 Grades & Echelons</h1>
        <p style="color: #7F8C8D;">Gestion des Echelles Salariales</p>
        <hr style="border: 1px solid #BDC3C7;">
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📊 Grades", "📐 Echelons"])

    with tab1:
        grades = db.get_all_grades()
        if grades:
            df = pd.DataFrame(grades)
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={
                             "code_grade": st.column_config.TextColumn("Code Grade"),
                             "salaire_base": st.column_config.NumberColumn("Salaire Base (DA)", format="%.2f"),
                             "increment_par_echelon": st.column_config.NumberColumn("Increment/Echelon (DA)", format="%.2f"),
                         })
        else:
            st.info("Aucun grade defini.")

        st.markdown("<hr>", unsafe_allow_html=True)
        with st.expander("➕ Ajouter un Grade"):
            with st.form("add_grade"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    g_code = st.text_input("Code Grade", placeholder="Ex: A1")
                with c2:
                    g_base = st.number_input("Salaire Base", min_value=0.0, value=30000.0, step=1000.0)
                with c3:
                    g_inc = st.number_input("Increment/Echelon", min_value=0.0, value=1500.0, step=100.0)
                if st.form_submit_button("Ajouter", use_container_width=True):
                    if g_code and db.create_grade(g_code.upper(), g_base, g_inc):
                        st.success(f"Grade {g_code.upper()} ajoute!")
                        st.rerun()
                    else:
                        st.error("Ce grade existe deja ou le code est invalide.")

    with tab2:
        echelons = db.get_all_echelons()
        if echelons:
            df = pd.DataFrame(echelons)
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={
                             "id_echelon": st.column_config.NumberColumn("ID"),
                             "numero_echelon": st.column_config.Number_column("Numero"),
                             "coefficient": st.column_config.NumberColumn("Coefficient", format="%.3f"),
                         })
        else:
            st.info("Aucun echelon defini.")

        st.markdown("<hr>", unsafe_allow_html=True)
        with st.expander("➕ Ajouter un Echelon"):
            with st.form("add_echelon"):
                c1, c2 = st.columns(2)
                with c1:
                    e_num = st.number_input("Numero d'echelon", min_value=1, max_value=50, value=13)
                with c2:
                    e_coef = st.number_input("Coefficient", min_value=0.5, value=1.24, step=0.01)
                if st.form_submit_button("Ajouter", use_container_width=True):
                    if db.create_echelon(int(e_num), e_coef):
                        st.success(f"Echelon {e_num} ajoute!")
                        st.rerun()
                    else:
                        st.error("Cet echelon existe deja.")


# ═════════════════════════════════════════
# PAGE: Rules - Primes & Retenues (Admin)
# ═════════════════════════════════════════
def render_rules():
    st.markdown("""
        <h1 style="color: #2C3E50;">⚙ Primes & Retenues</h1>
        <p style="color: #7F8C8D;">Configuration des Regles de Calcul</p>
        <hr style="border: 1px solid #BDC3C7;">
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["✚ Primes (Indemnites)", "✕ Retenues (Deductions)"])

    # ── Primes ──
    with tab1:
        primes = db.get_all_primes(active_only=False)
        if primes:
            df = pd.DataFrame(primes)
            df["active"] = df["active"].map({1: "✅ Active", 0: "❌ Inactive"})
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={
                             "id_prime": st.column_config.NumberColumn("ID"),
                             "nom_prime": st.column_config.TextColumn("Nom"),
                             "type_calcul": st.column_config.TextColumn("Type"),
                             "valeur": st.column_config.NumberColumn("Valeur", format="%.2f"),
                             "active": st.column_config.TextColumn("Statut"),
                         })
        else:
            st.info("Aucune prime definie.")

        st.markdown("<hr>", unsafe_allow_html=True)
        with st.expander("➕ Ajouter une Prime"):
            with st.form("add_prime"):
                p_nom = st.text_input("Nom", placeholder="Ex: prime_expertise")
                p_type = st.selectbox("Type de calcul", ["fixe", "pourcentage", "par_enfant"])
                p_val = st.number_input("Valeur", min_value=0.0, value=1000.0, step=100.0)
                if st.form_submit_button("Ajouter", use_container_width=True):
                    if p_nom and db.create_prime(p_nom, p_type, p_val):
                        st.success(f"Prime '{p_nom}' ajoutee!")
                        st.rerun()

        if primes:
            st.markdown("<hr>", unsafe_allow_html=True)
            with st.expander("🔄 Activer/Desactiver une Prime"):
                p_opts = {p["id_prime"]: f"{p['nom_prime']} ({p['type_calcul']})" for p in primes}
                sel_pid = st.selectbox("Selectionner", options=list(p_opts.keys()), format_func=lambda x: p_opts[x])
                p_data = next((p for p in primes if p["id_prime"] == sel_pid), None)
                if p_data:
                    new_state = st.checkbox("Active", value=bool(p_data["active"]))
                    if st.button("Mettre a jour"):
                        db.update_prime(sel_pid, active=int(new_state))
                        st.success("Statut mis a jour!")
                        st.rerun()

    # ── Retenues ──
    with tab2:
        retenues = db.get_all_retenues(active_only=False)
        if retenues:
            df = pd.DataFrame(retenues)
            df["active"] = df["active"].map({1: "✅ Active", 0: "❌ Inactive"})
            st.dataframe(df, use_container_width=True, hide_index=True,
                         column_config={
                             "id_retenue": st.column_config.NumberColumn("ID"),
                             "nom_retenue": st.column_config.TextColumn("Nom"),
                             "type_calcul": st.column_config.TextColumn("Type"),
                             "valeur": st.column_config.NumberColumn("Valeur", format="%.4f"),
                             "active": st.column_config.TextColumn("Statut"),
                         })
        else:
            st.info("Aucune retenue definie.")

        st.markdown("<hr>", unsafe_allow_html=True)
        with st.expander("➕ Ajouter une Retenue"):
            with st.form("add_retenue"):
                r_nom = st.text_input("Nom", placeholder="Ex: cotisation_mutuelle")
                r_type = st.selectbox("Type de calcul", ["pourcentage", "fixe"])
                r_val = st.number_input("Valeur (pourcentage = 0.09 pour 9%)", min_value=0.0,
                                         value=0.05, step=0.01, format="%.4f")
                if st.form_submit_button("Ajouter", use_container_width=True):
                    if r_nom and db.create_retenue(r_nom, r_type, r_val):
                        st.success(f"Retenue '{r_nom}' ajoutee!")
                        st.rerun()

        if retenues:
            st.markdown("<hr>", unsafe_allow_html=True)
            with st.expander("🔄 Activer/Desactiver une Retenue"):
                r_opts = {r["id_retenue"]: f"{r['nom_retenue']} ({r['type_calcul']})" for r in retenues}
                sel_rid = st.selectbox("Selectionner", options=list(r_opts.keys()), format_func=lambda x: r_opts[x])
                r_data = next((r for r in retenues if r["id_retenue"] == sel_rid), None)
                if r_data:
                    new_state = st.checkbox("Active", value=bool(r_data["active"]))
                    if st.button("Mettre a jour"):
                        db.update_retenue(sel_rid, active=int(new_state))
                        st.success("Statut mis a jour!")
                        st.rerun()


# ═════════════════════════════════════════
# PAGE: Monthly Payroll Processing (Admin)
# ═════════════════════════════════════════
def render_payroll():
    st.markdown("""
        <h1 style="color: #2C3E50;">🔄 Traitement de la Paie Mensuelle</h1>
        <p style="color: #7F8C8D;">Calcul et generation des salaires pour tous les employes actifs</p>
        <hr style="border: 1px solid #BDC3C7;">
    """, unsafe_allow_html=True)

    # Month selection
    c1, c2 = st.columns([1, 3])
    with c1:
        sel_year = st.selectbox("Annee", options=list(range(2023, 2028)), index=3)
    with c2:
        sel_month = st.selectbox("Mois", options=[
            (1, "Janvier"), (2, "Fevrier"), (3, "Mars"), (4, "Avril"),
            (5, "Mai"), (6, "Juin"), (7, "Juillet"), (8, "Aout"),
            (9, "Septembre"), (10, "Octobre"), (11, "Novembre"), (12, "Decembre")
        ], format_func=lambda x: x[1], index=datetime.now().month - 1)

    month_key = f"{sel_year}-{sel_month[0]:02d}-01"

    # Preview
    employes = db.get_all_employes()
    actifs = [e for e in employes if e["statut"] == "actif"]

    st.info(f"**{len(actifs)}** employes actifs seront traites pour **{sel_month[1]} {sel_year}**.")

    if st.button("▶ Lancer le Traitement", use_container_width=True, type="primary"):
        if not actifs:
            st.warning("Aucun employe actif a traiter.")
        else:
            with st.spinner("Traitement en cours..."):
                result = se.traiter_paie_mensuelle(month_key)

            st.success(f"✅ Traitement termine! {result['total_processed']} employes traites.")

            # Summary metrics
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Salaire Brut Total", f"{result['total_brut']:,.2f} DA")
            with c2:
                st.metric("Total Primes", f"{result['total_primes']:,.2f} DA")
            with c3:
                st.metric("Total Retenues", f"{result['total_retenues']:,.2f} DA")
            with c4:
                st.metric("Salaire Net Total", f"{result['total_net']:,.2f} DA")

            # Detailed breakdown
            st.subheader("Details par Employe")
            details = result["details"]
            if details:
                df_det = pd.DataFrame([{
                    "Nom": d["employe_nom"],
                    "Grade": d["code_grade"],
                    "Base": d["salaire_base"],
                    "Primes": d["total_primes"],
                    "Retenues": d["total_retenues"],
                    "Net": d["salaire_net"],
                } for d in details])
                st.dataframe(df_det, use_container_width=True, hide_index=True,
                             column_config={
                                 "Base": st.column_config.NumberColumn(format="%.2f DA"),
                                 "Primes": st.column_config.NumberColumn(format="%.2f DA"),
                                 "Retenues": st.column_config.NumberColumn(format="%.2f DA"),
                                 "Net": st.column_config.NumberColumn(format="%.2f DA"),
                             })

    # Already processed check
    existing = db.get_paie_by_month(month_key)
    if existing:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.info(f"📋 {len(existing)} fiches de paie existent deja pour {sel_month[1]} {sel_year}.")
        if st.button("Voir les fiches existantes"):
            st.session_state.view_month = month_key
            st.session_state.page = "payslips"
            st.rerun()


# ═════════════════════════════════════════
# PAGE: Payslips (Admin)
# ═════════════════════════════════════════
def render_payslips():
    st.markdown("""
        <h1 style="color: #2C3E50;">📜 Bulletins de Paie</h1>
        <p style="color: #7F8C8D;">Visualisation et impression des bulletins</p>
        <hr style="border: 1px solid #BDC3C7;">
    """, unsafe_allow_html=True)

    # Month filter
    monthly_data = db.get_monthly_payroll_totals()
    if not monthly_data:
        st.info("Aucune paie traitee. Allez dans 'Traitement Mensuel' pour generer des paies.")
        return

    month_opts = {m["mois"]: datetime.strptime(m["mois"], "%Y-%m-%d").strftime("%B %Y").capitalize()
                  for m in monthly_data}
    view_month = st.session_state.get("view_month", list(month_opts.keys())[0])

    sel_month = st.selectbox("Selectionner un mois", options=list(month_opts.keys()),
                              index=list(month_opts.keys()).index(view_month) if view_month in month_opts else 0,
                              format_func=lambda x: month_opts[x])

    paies = db.get_paie_by_month(sel_month)
    if not paies:
        st.info("Aucune paie pour ce mois.")
        return

    st.subheader(f"Bulletins de {month_opts[sel_month]} ({len(paies)} employes)")

    for p in paies:
        html_card = generate_payslip_summary_card(p)
        st.markdown(html_card, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("📄 Voir le Bulletin", key=f"view_{p['id_paie']}"):
                html_payslip = generate_payslip_html(p["id_paie"])
                st.session_state.current_payslip = html_payslip
                st.session_state.current_payslip_emp = p.get("nom", "Employe")
                st.session_state.show_payslip = True
        with col2:
            status_opts = ["en_attente", "traite", "paye"]
            current = p["statut"]
            new_stat = st.selectbox("Statut", status_opts,
                                    index=status_opts.index(current),
                                    key=f"stat_{p['id_paie']}", label_visibility="collapsed")
            if new_stat != current:
                db.update_paie_status(p["id_paie"], new_stat)
                st.rerun()

    # Show payslip popup
    if st.session_state.get("show_payslip", False):
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader(f"Bulletin de Paie - {st.session_state.get('current_payslip_emp', '')}")
        st.components.v1.html(st.session_state.current_payslip, height=1200, scrolling=True)
        if st.button("❌ Fermer"):
            st.session_state.show_payslip = False
            del st.session_state.current_payslip
            st.rerun()


# ═════════════════════════════════════════
# PAGE: Salary History (Admin)
# ═════════════════════════════════════════
def render_history():
    st.markdown("""
        <h1 style="color: #2C3E50;">📈 Historique des Salaires</h1>
        <p style="color: #7F8C8D;">Suivi mensuel par employe</p>
        <hr style="border: 1px solid #BDC3C7;">
    """, unsafe_allow_html=True)

    employes = db.get_all_employes()
    if not employes:
        st.info("Aucun employe enregistre.")
        return

    emp_opts = {e["id_employe"]: f"{e['nom']} ({e['code_grade']})" for e in employes}
    sel_emp = st.selectbox("Selectionner un employe", options=list(emp_opts.keys()),
                            format_func=lambda x: emp_opts[x])

    paies = db.get_paie_by_employee(sel_emp)
    if not paies:
        st.info("Aucune paie pour cet employe.")
        return

    # Table
    df = pd.DataFrame([{
        "Mois": datetime.strptime(p["mois"], "%Y-%m-%d").strftime("%b %Y").capitalize(),
        "Brut": p["salaire_brut"],
        "Primes": p["total_primes"],
        "Retenues": p["total_retenues"],
        "Net": p["salaire_net"],
        "Statut": p["statut"],
    } for p in paies])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Chart
    df["mois_dt"] = pd.to_datetime([p["mois"] for p in paies])
    df = df.sort_values("mois_dt")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Mois"], y=df["Net"], name="Net", marker_color="#27AE60"))
    fig.add_trace(go.Bar(x=df["Mois"], y=df["Retenues"], name="Retenues", marker_color="#E74C3C"))
    fig.add_trace(go.Bar(x=df["Mois"], y=df["Primes"], name="Primes", marker_color="#3498DB"))
    fig.update_layout(
        barmode="group", xaxis_title="Mois", yaxis_title="Montant (DA)",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════
# PAGE: Import / Export (Admin)
# ═════════════════════════════════════════
def render_import_export():
    st.markdown("""
        <h1 style="color: #2C3E50;">📁 Import / Export</h1>
        <p style="color: #7F8C8D;">Import CSV des employes et export Excel des paies</p>
        <hr style="border: 1px solid #BDC3C7;">
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📥 Import Employes (CSV)", "📤 Export Paies (Excel)"])

    # ── Import ──
    with tab1:
        st.subheader("Importer des Employes depuis CSV")
        st.markdown("""
            **Format CSV attendu:**
            ```
            nom,date_embauche,compte_bancaire,poste,statut,nombre_enfants,code_grade,numero_echelon
            Ahmed Benali,2020-01-15,00799999000000000001,Comptable,actif,2,A1,3
            ```
        """)
        uploaded = st.file_uploader("Choisir un fichier CSV", type=["csv"])
        if uploaded:
            try:
                df = pd.read_csv(uploaded)
                st.write(f"**{len(df)}** lignes detectees.")
                st.dataframe(df.head(), use_container_width=True)

                if st.button("📥 Importer", use_container_width=True, type="primary"):
                    # Map echelon numbers to IDs
                    echelons = db.get_all_echelons()
                    ech_map = {e["numero_echelon"]: e["id_echelon"] for e in echelons}

                    employees = []
                    for _, row in df.iterrows():
                        ech_num = int(row.get("numero_echelon", 1))
                        ech_id = ech_map.get(ech_num, 1)
                        employees.append({
                            "nom": str(row.get("nom", "")),
                            "date_embauche": str(row.get("date_embauche", "2020-01-01")),
                            "compte_bancaire": str(row.get("compte_bancaire", "")),
                            "poste": str(row.get("poste", "")),
                            "statut": str(row.get("statut", "actif")),
                            "nombre_enfants": int(row.get("nombre_enfants", 0)),
                            "code_grade": str(row.get("code_grade", "C1")),
                            "id_echelon": ech_id,
                        })

                    success, failed = db.bulk_insert_employes(employees)
                    st.success(f"Import termine: {success} reussi(s), {failed} echoue(s).")
            except Exception as e:
                st.error(f"Erreur d'import: {e}")

    # ── Export ──
    with tab2:
        st.subheader("Exporter les Paies vers Excel")

        monthly_data = db.get_monthly_payroll_totals()
        if not monthly_data:
            st.info("Aucune donnee de paie a exporter.")
            return

        month_opts = {m["mois"]: datetime.strptime(m["mois"], "%Y-%m-%d").strftime("%B %Y").capitalize()
                      for m in monthly_data}
        sel_month = st.selectbox("Selectionner un mois a exporter", options=list(month_opts.keys()),
                                  format_func=lambda x: month_opts[x])

        if st.button("📤 Generer le Fichier Excel", use_container_width=True, type="primary"):
            paies = db.get_paie_by_month(sel_month)
            if paies:
                # Create Excel file in memory
                df = pd.DataFrame([{
                    "ID": p["id_paie"],
                    "Nom": p.get("nom", ""),
                    "Poste": p.get("poste", ""),
                    "Grade": p.get("code_grade", ""),
                    "Salaire Brut": p["salaire_brut"],
                    "Total Primes": p["total_primes"],
                    "Total Retenues": p["total_retenues"],
                    "Salaire Net": p["salaire_net"],
                    "Statut": p["statut"],
                } for p in paies])

                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df.to_excel(writer, sheet_name="Paie", index=False)
                    workbook = writer.book
                    worksheet = writer.sheets["Paie"]

                    # Formatting
                    header_fmt = workbook.add_format({
                        "bold": True, "bg_color": "#2C3E50", "font_color": "white",
                        "align": "center", "valign": "vcenter"
                    })
                    money_fmt = workbook.add_format({"num_format": "#,##0.00 DA", "align": "right"})

                    for col_num, value in enumerate(df.columns.values):
                        worksheet.write(0, col_num, value, header_fmt)

                    for row_num in range(len(df)):
                        for col_num, col_name in enumerate(df.columns):
                            if "Salaire" in col_name or "Total" in col_name:
                                worksheet.write(row_num + 1, col_num, df.iloc[row_num, col_num], money_fmt)

                    worksheet.set_column(0, 0, 8)
                    worksheet.set_column(1, 1, 25)
                    worksheet.set_column(2, 2, 20)
                    worksheet.set_column(3, 7, 15)

                buffer.seek(0)
                month_file = month_opts[sel_month].replace(" ", "_")
                st.download_button(
                    label="📥 Telecharger le fichier Excel",
                    data=buffer.getvalue(),
                    file_name=f"paie_{month_file}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )


# ═════════════════════════════════════════
# PAGE: Employee Dashboard
# ═════════════════════════════════════════
def render_employee_dashboard():
    emp_id = get_current_user_id()
    if not emp_id:
        st.error("Votre compte n'est associe a aucun employe.")
        return

    emp = db.get_employe_by_id(emp_id)
    if not emp:
        st.error("Informations employe non trouvees.")
        return

    st.markdown(f"""
        <h1 style="color: #2C3E50;">👤 Mon Profil</h1>
        <p style="color: #7F8C8D;">Espace employe - {emp['nom']}</p>
        <hr style="border: 1px solid #BDC3C7;">
    """, unsafe_allow_html=True)

    # Profile card
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div style="background: #EBF5FB; padding: 20px; border-radius: 10px; text-align: center;">
                <h3 style="color: #2C3E50; margin: 0;">📋 {emp['code_grade']}</h3>
                <p style="color: #7F8C8D; margin: 5px 0;">Grade | Echelon {emp['numero_echelon']}</p>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        anciennete = se.calculer_anciennete(emp["date_embauche"])
        st.markdown(f"""
            <div style="background: #EAFAF1; padding: 20px; border-radius: 10px; text-align: center;">
                <h3 style="color: #27AE60; margin: 0;">📅 {anciennete} ans</h3>
                <p style="color: #7F8C8D; margin: 5px 0;">Anciennete</p>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        salaire_base = se.calculer_salaire_base(emp["code_grade"], emp["id_echelon"])
        st.markdown(f"""
            <div style="background: #2C3E50; color: white; padding: 20px; border-radius: 10px; text-align: center;">
                <h3 style="margin: 0;">💰 {salaire_base:,.2f} DA</h3>
                <p style="color: #BDC3C7; margin: 5px 0;">Salaire de Base</p>
            </div>
        """, unsafe_allow_html=True)

    # Details
    st.markdown("<hr>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Informations Personnelles")
        st.write(f"**Nom:** {emp['nom']}")
        st.write(f"**Poste:** {emp.get('poste', 'Non defini')}")
        st.write(f"**Date d'embauche:** {emp['date_embauche']}")
        st.write(f"**Compte Bancaire:** {emp.get('compte_bancaire', 'N/A') or 'N/A'}")
    with c2:
        st.subheader("Situation Familiale")
        st.write(f"**Nombre d'enfants:** {emp.get('nombre_enfants', 0)}")
        st.write(f"**Statut:** {emp['statut'].upper()}")

    # Recent payslip
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("Dernier Bulletin")
    paies = db.get_paie_by_employee(emp_id)
    if paies:
        latest = paies[0]
        card = generate_payslip_summary_card(latest)
        st.markdown(card, unsafe_allow_html=True)
        if st.button("📄 Voir le Bulletin Complet"):
            html = generate_payslip_html(latest["id_paie"])
            st.session_state.current_payslip = html
            st.session_state.current_payslip_emp = emp["nom"]
            st.session_state.show_payslip = True
            st.session_state.emp_view = True
            st.rerun()
    else:
        st.info("Aucun bulletin disponible.")


# ═════════════════════════════════════════
# PAGE: My Payslips (Employee)
# ═════════════════════════════════════════
def render_my_payslips():
    emp_id = get_current_user_id()
    if not emp_id:
        st.error("Votre compte n'est associe a aucun employe.")
        return

    emp = db.get_employe_by_id(emp_id)
    st.markdown(f"""
        <h1 style="color: #2C3E50;">📜 Mes Bulletins de Paie</h1>
        <p style="color: #7F8C8D;">{emp['nom'] if emp else 'Employe'}</p>
        <hr style="border: 1px solid #BDC3C7;">
    """, unsafe_allow_html=True)

    paies = db.get_paie_by_employee(emp_id)
    if not paies:
        st.info("Aucun bulletin de paie disponible.")
        return

    for p in paies:
        card = generate_payslip_summary_card(p)
        st.markdown(card, unsafe_allow_html=True)
        if st.button("📄 Voir le Bulletin", key=f"my_{p['id_paie']}"):
            html = generate_payslip_html(p["id_paie"])
            st.session_state.current_payslip = html
            st.session_state.current_payslip_emp = emp["nom"] if emp else ""
            st.session_state.show_payslip = True
            st.session_state.emp_view = True
            st.rerun()

    if st.session_state.get("show_payslip", False) and st.session_state.get("emp_view", False):
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Bulletin de Paie")
        st.components.v1.html(st.session_state.current_payslip, height=1200, scrolling=True)
        if st.button("❌ Fermer"):
            st.session_state.show_payslip = False
            st.session_state.emp_view = False
            del st.session_state.current_payslip
            st.rerun()


# ═════════════════════════════════════════
# MAIN ROUTER
# ═════════════════════════════════════════
if not st.session_state.get("authenticated", False):
    login_page()
else:
    nav_sidebar()
    page = st.session_state.get("page", "dashboard")

    if page == "dashboard":
        render_dashboard()
    elif page == "employees":
        render_employees()
    elif page == "grades":
        render_grades()
    elif page == "rules":
        render_rules()
    elif page == "payroll":
        render_payroll()
    elif page == "payslips":
        render_payslips()
    elif page == "history":
        render_history()
    elif page == "import_export":
        render_import_export()
    elif page == "employee_dashboard":
        render_employee_dashboard()
    elif page == "my_payslips":
        render_my_payslips()
    else:
        render_dashboard()
