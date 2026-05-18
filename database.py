"""
database.py - Database initialization and CRUD operations for the Salary Management System.
All SQLite database operations are centralized here.
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "salary_db.sqlite")


def get_connection() -> sqlite3.Connection:
    """Create and return a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """Initialize the full database schema with all tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Table: Grade (salary scale per grade)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grade (
            code_grade TEXT PRIMARY KEY,
            salaire_base REAL NOT NULL,
            increment_par_echelon REAL DEFAULT 0
        )
    """)

    # Table: Echelon (step definition)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS echelon (
            id_echelon INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_echelon INTEGER NOT NULL UNIQUE,
            coefficient REAL DEFAULT 1.0
        )
    """)

    # Table: Employe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employe (
            id_employe INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            date_embauche TEXT NOT NULL,
            compte_bancaire TEXT,
            poste TEXT,
            statut TEXT CHECK (statut IN ('actif', 'en_conge', 'retraite', 'licencie')) DEFAULT 'actif',
            nombre_enfants INTEGER DEFAULT 0,
            code_grade TEXT NOT NULL,
            id_echelon INTEGER NOT NULL,
            FOREIGN KEY (code_grade) REFERENCES grade(code_grade),
            FOREIGN KEY (id_echelon) REFERENCES echelon(id_echelon)
        )
    """)

    # Table: Prime (Allowance type)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prime (
            id_prime INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_prime TEXT NOT NULL UNIQUE,
            type_calcul TEXT CHECK (type_calcul IN ('fixe', 'pourcentage', 'par_enfant')) NOT NULL,
            valeur REAL NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    # Table: Retenue (Deduction type)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS retenue (
            id_retenue INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_retenue TEXT NOT NULL UNIQUE,
            type_calcul TEXT CHECK (type_calcul IN ('fixe', 'pourcentage')) NOT NULL DEFAULT 'pourcentage',
            valeur REAL NOT NULL,
            active INTEGER DEFAULT 1
        )
    """)

    # Table: Utilisateur (login accounts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS utilisateur (
            id_utilisateur INTEGER PRIMARY KEY AUTOINCREMENT,
            id_employe INTEGER UNIQUE,
            nom_utilisateur TEXT NOT NULL UNIQUE,
            mot_de_passe_hash TEXT NOT NULL,
            role TEXT CHECK (role IN ('admin', 'employe')) NOT NULL DEFAULT 'employe',
            FOREIGN KEY (id_employe) REFERENCES employe(id_employe) ON DELETE SET NULL
        )
    """)

    # Table: Paie (Payroll record)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paie (
            id_paie INTEGER PRIMARY KEY AUTOINCREMENT,
            id_employe INTEGER NOT NULL,
            mois TEXT NOT NULL,
            salaire_brut REAL NOT NULL,
            total_primes REAL DEFAULT 0,
            total_retenues REAL DEFAULT 0,
            salaire_net REAL NOT NULL,
            statut TEXT DEFAULT 'en_attente' CHECK (statut IN ('en_attente', 'traite', 'paye')),
            FOREIGN KEY (id_employe) REFERENCES employe(id_employe) ON DELETE CASCADE,
            UNIQUE(id_employe, mois)
        )
    """)

    # Junction: paie_prime
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paie_prime (
            id_paie INTEGER NOT NULL,
            id_prime INTEGER NOT NULL,
            montant_applique REAL NOT NULL,
            PRIMARY KEY (id_paie, id_prime),
            FOREIGN KEY (id_paie) REFERENCES paie(id_paie) ON DELETE CASCADE,
            FOREIGN KEY (id_prime) REFERENCES prime(id_prime) ON DELETE CASCADE
        )
    """)

    # Junction: paie_retenue
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paie_retenue (
            id_paie INTEGER NOT NULL,
            id_retenue INTEGER NOT NULL,
            montant_retenu REAL NOT NULL,
            PRIMARY KEY (id_paie, id_retenue),
            FOREIGN KEY (id_paie) REFERENCES paie(id_paie) ON DELETE CASCADE,
            FOREIGN KEY (id_retenue) REFERENCES retenue(id_retenue) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    seed_default_data()


def seed_default_data():
    """Insert default reference data (grades, echelons, primes, retenues, admin user)."""
    conn = get_connection()
    cursor = conn.cursor()

    # Default grades (Algerian public administration inspired)
    grades = [
        ("A1", 48000, 2400),
        ("A2", 42000, 2100),
        ("A3", 36000, 1800),
        ("B1", 30000, 1500),
        ("B2", 26000, 1300),
        ("C1", 22000, 1100),
        ("C2", 18000, 900),
        ("D1", 15000, 750),
        ("D2", 12000, 600),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO grade (code_grade, salaire_base, increment_par_echelon) VALUES (?, ?, ?)",
        grades
    )

    # Default echelons (1-12)
    for i in range(1, 13):
        cursor.execute(
            "INSERT OR IGNORE INTO echelon (numero_echelon, coefficient) VALUES (?, ?)",
            (i, 1.0 + (i - 1) * 0.02)
        )

    # Default allowances (primes)
    primes = [
        ("prime_familiale", "par_enfant", 600),
        ("prime_de_residence", "pourcentage", 0.10),
        ("prime_danciennete", "pourcentage", 0.02),
        ("prime_de_transport", "fixe", 1500),
        ("prime_de_panier", "fixe", 1200),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO prime (nom_prime, type_calcul, valeur) VALUES (?, ?, ?)",
        primes
    )

    # Default deductions (retenues) - Algerian CNAS/CNR/IRG
    retenues = [
        ("CNAS", "pourcentage", 0.09),
        ("CNR", "pourcentage", 0.065),
        ("IRG", "pourcentage", 0.05),
        ("assurance_maladie", "pourcentage", 0.025),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO retenue (nom_retenue, type_calcul, valeur) VALUES (?, ?, ?)",
        retenues
    )

    # Create default admin user (password: admin123)
    from werkzeug.security import generate_password_hash
    admin_hash = generate_password_hash("admin123")
    cursor.execute(
        """INSERT OR IGNORE INTO utilisateur
           (nom_utilisateur, mot_de_passe_hash, role)
           VALUES (?, ?, ?)""",
        ("admin", admin_hash, "admin")
    )

    conn.commit()
    conn.close()


# ============================
# CRUD: Employe
# ============================

def create_employe(nom: str, date_embauche: str, compte_bancaire: str, poste: str,
                   statut: str, nombre_enfants: int, code_grade: str, id_echelon: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO employe (nom, date_embauche, compte_bancaire, poste, statut, nombre_enfants, code_grade, id_echelon)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (nom, date_embauche, compte_bancaire, poste, statut, nombre_enfants, code_grade, id_echelon))
    emp_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return emp_id


def get_all_employes() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.*, g.salaire_base, g.increment_par_echelon, ec.numero_echelon, ec.coefficient
        FROM employe e
        JOIN grade g ON e.code_grade = g.code_grade
        JOIN echelon ec ON e.id_echelon = ec.id_echelon
        ORDER BY e.id_employe DESC
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_employe_by_id(emp_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.*, g.salaire_base, g.increment_par_echelon, ec.numero_echelon, ec.coefficient
        FROM employe e
        JOIN grade g ON e.code_grade = g.code_grade
        JOIN echelon ec ON e.id_echelon = ec.id_echelon
        WHERE e.id_employe = ?
    """, (emp_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_employe(emp_id: int, **fields) -> bool:
    allowed = {"nom", "date_embauche", "compte_bancaire", "poste", "statut",
               "nombre_enfants", "code_grade", "id_echelon"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [emp_id]
    cursor.execute(f"UPDATE employe SET {set_clause} WHERE id_employe = ?", values)
    conn.commit()
    conn.close()
    return True


def delete_employe(emp_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM employe WHERE id_employe = ?", (emp_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ============================
# CRUD: Grade
# ============================

def get_all_grades() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grade ORDER BY code_grade")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def create_grade(code_grade: str, salaire_base: float, increment_par_echelon: float) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO grade (code_grade, salaire_base, increment_par_echelon) VALUES (?, ?, ?)",
                       (code_grade, salaire_base, increment_par_echelon))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_grade(code_grade: str, salaire_base: float, increment_par_echelon: float) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE grade SET salaire_base = ?, increment_par_echelon = ? WHERE code_grade = ?",
                   (salaire_base, increment_par_echelon, code_grade))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_grade(code_grade: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM grade WHERE code_grade = ?", (code_grade,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ============================
# CRUD: Echelon
# ============================

def get_all_echelons() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM echelon ORDER BY numero_echelon")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def create_echelon(numero_echelon: int, coefficient: float) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO echelon (numero_echelon, coefficient) VALUES (?, ?)",
                       (numero_echelon, coefficient))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# ============================
# CRUD: Prime
# ============================

def get_all_primes(active_only: bool = True) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    sql = "SELECT * FROM prime"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY id_prime"
    cursor.execute(sql)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def create_prime(nom_prime: str, type_calcul: str, valeur: float) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO prime (nom_prime, type_calcul, valeur) VALUES (?, ?, ?)",
                       (nom_prime, type_calcul, valeur))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_prime(prime_id: int, **fields) -> bool:
    allowed = {"nom_prime", "type_calcul", "valeur", "active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [prime_id]
    cursor.execute(f"UPDATE prime SET {set_clause} WHERE id_prime = ?", values)
    conn.commit()
    conn.close()
    return True


# ============================
# CRUD: Retenue
# ============================

def get_all_retenues(active_only: bool = True) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    sql = "SELECT * FROM retenue"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY id_retenue"
    cursor.execute(sql)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def create_retenue(nom_retenue: str, type_calcul: str, valeur: float) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO retenue (nom_retenue, type_calcul, valeur) VALUES (?, ?, ?)",
                       (nom_retenue, type_calcul, valeur))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_retenue(retenue_id: int, **fields) -> bool:
    allowed = {"nom_retenue", "type_calcul", "valeur", "active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [retenue_id]
    cursor.execute(f"UPDATE retenue SET {set_clause} WHERE id_retenue = ?", values)
    conn.commit()
    conn.close()
    return True


# ============================
# CRUD: Paie (Payroll)
# ============================

def create_paie(emp_id: int, month: str, salaire_brut: float, total_primes: float,
                total_retenues: float, salaire_net: float) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO paie (id_employe, mois, salaire_brut, total_primes, total_retenues, salaire_net, statut)
        VALUES (?, ?, ?, ?, ?, ?, 'traite')
    """, (emp_id, month, salaire_brut, total_primes, total_retenues, salaire_net))
    paie_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return paie_id


def get_paie_by_month(month: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, e.nom, e.poste, e.code_grade
        FROM paie p
        JOIN employe e ON p.id_employe = e.id_employe
        WHERE p.mois = ?
        ORDER BY e.nom
    """, (month,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_paie_by_employee(emp_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, e.nom, e.poste, e.code_grade
        FROM paie p
        JOIN employe e ON p.id_employe = e.id_employe
        WHERE p.id_employe = ?
        ORDER BY p.mois DESC
    """, (emp_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_paie_details(paie_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, e.nom, e.poste, e.code_grade, e.compte_bancaire, e.nombre_enfants,
               g.salaire_base, g.increment_par_echelon, ec.numero_echelon
        FROM paie p
        JOIN employe e ON p.id_employe = e.id_employe
        JOIN grade g ON e.code_grade = g.code_grade
        JOIN echelon ec ON e.id_echelon = ec.id_echelon
        WHERE p.id_paie = ?
    """, (paie_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_primes_for_paie(paie_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pp.*, pr.nom_prime, pr.type_calcul
        FROM paie_prime pp
        JOIN prime pr ON pp.id_prime = pr.id_prime
        WHERE pp.id_paie = ?
    """, (paie_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_retenues_for_paie(paie_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pr.*, r.nom_retenue, r.type_calcul
        FROM paie_retenue pr
        JOIN retenue r ON pr.id_retenue = r.id_retenue
        WHERE pr.id_paie = ?
    """, (paie_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def update_paie_status(paie_id: int, status: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE paie SET statut = ? WHERE id_paie = ?", (status, paie_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def save_paie_prime(paie_id: int, prime_id: int, montant: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO paie_prime (id_paie, id_prime, montant_applique) VALUES (?, ?, ?)",
        (paie_id, prime_id, montant)
    )
    conn.commit()
    conn.close()


def save_paie_retenue(paie_id: int, retenue_id: int, montant: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO paie_retenue (id_paie, id_retenue, montant_retenu) VALUES (?, ?, ?)",
        (paie_id, retenue_id, montant)
    )
    conn.commit()
    conn.close()


# ============================
# CRUD: Utilisateur
# ============================

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.*, e.nom as employe_nom, e.id_employe as emp_id
        FROM utilisateur u
        LEFT JOIN employe e ON u.id_employe = e.id_employe
        WHERE u.nom_utilisateur = ?
    """, (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_utilisateur(nom_utilisateur: str, password_hash: str, role: str = "employe",
                       id_employe: Optional[int] = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO utilisateur (nom_utilisateur, mot_de_passe_hash, role, id_employe) VALUES (?, ?, ?, ?)",
            (nom_utilisateur, password_hash, role, id_employe)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_all_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.*, e.nom as employe_nom
        FROM utilisateur u
        LEFT JOIN employe e ON u.id_employe = e.id_employe
        ORDER BY u.id_utilisateur
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# ============================
# Dashboard / Stats
# ============================

def get_dashboard_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM employe WHERE statut = 'actif'")
    total_active = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM employe")
    total_employees = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM paie WHERE statut = 'en_attente'")
    pending_payrolls = cursor.fetchone()["total"]

    cursor.execute("SELECT COALESCE(SUM(salaire_net), 0) as total FROM paie WHERE statut = 'traite'")
    total_processed = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(DISTINCT mois) as total FROM paie")
    total_months = cursor.fetchone()["total"]

    conn.close()
    return {
        "total_active": total_active,
        "total_employees": total_employees,
        "pending_payrolls": pending_payrolls,
        "total_processed": total_processed,
        "total_months": total_months,
    }


def get_monthly_payroll_totals() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mois,
               COUNT(*) as nb_employes,
               SUM(salaire_brut) as total_brut,
               SUM(total_primes) as total_primes,
               SUM(total_retenues) as total_retenues,
               SUM(salaire_net) as total_net
        FROM paie
        GROUP BY mois
        ORDER BY mois DESC
        LIMIT 12
    """)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# ============================
# Import / Bulk
# ============================

def bulk_insert_employes(employees: List[Dict[str, Any]]) -> Tuple[int, int]:
    """Bulk insert employees. Returns (success_count, fail_count)."""
    conn = get_connection()
    cursor = conn.cursor()
    success = 0
    failed = 0
    for emp in employees:
        try:
            cursor.execute("""
                INSERT INTO employe (nom, date_embauche, compte_bancaire, poste, statut, nombre_enfants, code_grade, id_echelon)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (emp["nom"], emp["date_embauche"], emp.get("compte_bancaire", ""),
                  emp.get("poste", ""), emp.get("statut", "actif"),
                  emp.get("nombre_enfants", 0), emp["code_grade"], emp["id_echelon"]))
            success += 1
        except Exception:
            failed += 1
    conn.commit()
    conn.close()
    return success, failed
