"""
auth.py - Authentication and session management for Salary Management System.
Handles role-based access control (Admin vs Employee).
"""

import streamlit as st
from werkzeug.security import check_password_hash, generate_password_hash
import database as db


def init_session_state():
    """Initialize all session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "role" not in st.session_state:
        st.session_state.role = None
    if "emp_id" not in st.session_state:
        st.session_state.emp_id = None
    if "nom" not in st.session_state:
        st.session_state.nom = None
    if "page" not in st.session_state:
        st.session_state.page = "login"


def login(username: str, password: str) -> bool:
    """Authenticate user and populate session state."""
    user = db.get_user_by_username(username)
    if user and check_password_hash(user["mot_de_passe_hash"], password):
        st.session_state.authenticated = True
        st.session_state.username = user["nom_utilisateur"]
        st.session_state.role = user["role"]
        st.session_state.emp_id = user.get("emp_id")
        st.session_state.nom = user.get("employe_nom", user["nom_utilisateur"])
        st.session_state.page = "dashboard"
        return True
    return False


def logout():
    """Clear session state and log out."""
    keys = ["authenticated", "username", "role", "emp_id", "nom", "page"]
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.authenticated = False
    st.session_state.page = "login"


def require_auth():
    """Decorator pattern: redirect to login if not authenticated."""
    if not st.session_state.get("authenticated", False):
        st.session_state.page = "login"
        return False
    return True


def require_admin():
    """Check if current user is admin."""
    return st.session_state.get("role") == "admin"


def is_admin() -> bool:
    """Return True if current user is admin."""
    return st.session_state.get("role") == "admin"


def get_current_user_id() -> int:
    """Return the employee ID of the currently logged-in user."""
    return st.session_state.get("emp_id", 0)


def login_page():
    """Render the login page."""
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style="text-align: center; padding: 30px 0;">
                <h1 style="color: #2C3E50; font-size: 2.5em;">🏛 State Salary Management</h1>
                <p style="color: #7F8C8D; font-size: 1.1em;">Ministere des Finances</p>
                <hr style="border: 1px solid #BDC3C7; margin: 20px 0;">
            </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=True):
            st.markdown("<h3 style='text-align: center; color: #2C3E50;'>Connexion</h3>", unsafe_allow_html=True)
            username = st.text_input("Nom d'utilisateur", placeholder="Entrez votre identifiant")
            password = st.text_input("Mot de passe", type="password", placeholder="Entrez votre mot de passe")
            submitted = st.form_submit_button("Se Connecter", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Veuillez remplir tous les champs.")
                elif login(username, password):
                    st.success(f"Bienvenue, {st.session_state.nom}!")
                    st.rerun()
                else:
                    st.error("Nom d'utilisateur ou mot de passe incorrect.")

        st.markdown("""
            <div style="text-align: center; padding: 20px; background: #EBF5FB; border-radius: 10px; margin-top: 20px;">
                <p style="color: #2C3E50; font-size: 0.9em;">
                    <strong>Compte par defaut:</strong><br>
                    Admin: <code>admin</code> / <code>admin123</code>
                </p>
            </div>
        """, unsafe_allow_html=True)


def nav_sidebar():
    """Render navigation sidebar based on user role."""
    with st.sidebar:
        st.markdown(f"""
            <div style="padding: 10px 0; text-align: center;">
                <h3 style="color: #2C3E50;">🏛 Gestion des Salaires</h3>
                <p style="color: #7F8C8D; font-size: 0.85em;">
                    {st.session_state.get('nom', 'Utilisateur')}
                    <br><span style="color: #E67E22;">{'👤 Admin' if is_admin() else '👷 Employe'}</span>
                </p>
            </div>
            <hr style="border: 1px solid #BDC3C7;">
        """, unsafe_allow_html=True)

        if is_admin():
            st.markdown("<p style='color: #7F8C8D; font-size: 0.8em;'>📊 TABLEAU DE BORD</p>", unsafe_allow_html=True)
            if st.button("🏠 Tableau de Bord", use_container_width=True):
                st.session_state.page = "dashboard"
                st.rerun()

            st.markdown("<p style='color: #7F8C8D; font-size: 0.8em; margin-top: 15px;'>👥 GESTION DU PERSONNEL</p>", unsafe_allow_html=True)
            if st.button("👥 Employes", use_container_width=True):
                st.session_state.page = "employees"
                st.rerun()
            if st.button("📋 Grades & Echelons", use_container_width=True):
                st.session_state.page = "grades"
                st.rerun()

            st.markdown("<p style='color: #7F8C8D; font-size: 0.8em; margin-top: 15px;'>💰 GESTION DE LA PAIE</p>", unsafe_allow_html=True)
            if st.button("⚙ Primes & Retenues", use_container_width=True):
                st.session_state.page = "rules"
                st.rerun()
            if st.button("🔄 Traitement Mensuel", use_container_width=True):
                st.session_state.page = "payroll"
                st.rerun()
            if st.button("📜 Bulletins de Paie", use_container_width=True):
                st.session_state.page = "payslips"
                st.rerun()
            if st.button("📈 Historique des Salaires", use_container_width=True):
                st.session_state.page = "history"
                st.rerun()

            st.markdown("<p style='color: #7F8C8D; font-size: 0.8em; margin-top: 15px;'>📁 IMPORT/EXPORT</p>", unsafe_allow_html=True)
            if st.button("📥 Import / 📤 Export", use_container_width=True):
                st.session_state.page = "import_export"
                st.rerun()

        else:
            # Employee view
            st.markdown("<p style='color: #7F8C8D; font-size: 0.8em;'>👤 ESPACE EMPLOYE</p>", unsafe_allow_html=True)
            if st.button("🏠 Mon Profil", use_container_width=True):
                st.session_state.page = "employee_dashboard"
                st.rerun()
            if st.button("📜 Mes Bulletins", use_container_width=True):
                st.session_state.page = "my_payslips"
                st.rerun()

        st.markdown("<hr style='border: 1px solid #BDC3C7;'>", unsafe_allow_html=True)
        if st.button("🚪 Deconnexion", use_container_width=True, type="secondary"):
            logout()
            st.rerun()
