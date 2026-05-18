"""
salary_engine.py - Core salary calculation engine.
Handles: basic salary computation, allowances, deductions, net salary.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import database as db


def calculer_anciennete(date_embauche: str) -> int:
    """Calculate years of service from hire date."""
    hire = datetime.strptime(date_embauche, "%Y-%m-%d")
    today = datetime.now()
    years = today.year - hire.year
    if (today.month, today.day) < (hire.month, hire.day):
        years -= 1
    return max(0, years)


def calculer_salaire_base(code_grade: str, id_echelon: int) -> float:
    """Calculate base salary = grade_base + (step-1) * increment."""
    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT salaire_base, increment_par_echelon FROM grade WHERE code_grade = ?", (code_grade,))
    grade_row = cursor.fetchone()

    cursor.execute("SELECT numero_echelon FROM echelon WHERE id_echelon = ?", (id_echelon,))
    echel_row = cursor.fetchone()
    conn.close()

    if not grade_row or not echel_row:
        return 0.0

    base = grade_row["salaire_base"]
    increment = grade_row["increment_par_echelon"]
    step = echel_row["numero_echelon"]

    return base + (step - 1) * increment


def calculer_primes(salaire_base: float, nombre_enfants: int, date_embauche: str,
                    active_only: bool = True) -> List[Dict[str, Any]]:
    """Calculate all active allowances for an employee."""
    primes_rules = db.get_all_primes(active_only=active_only)
    anciennete = calculer_anciennete(date_embauche)
    result = []

    for rule in primes_rules:
        nom = rule["nom_prime"]
        calc_type = rule["type_calcul"]
        valeur = rule["valeur"]

        if calc_type == "fixe":
            montant = valeur
        elif calc_type == "pourcentage":
            if "anciennete" in nom.lower():
                # Seniority: percentage per year of service
                montant = salaire_base * valeur * anciennete
            else:
                montant = salaire_base * valeur
        elif calc_type == "par_enfant":
            montant = valeur * nombre_enfants
        else:
            montant = 0

        result.append({
            "id_prime": rule["id_prime"],
            "nom_prime": nom,
            "type_calcul": calc_type,
            "valeur": valeur,
            "montant": round(montant, 2),
        })

    return result


def calculer_retenues(salaire_brut: float, total_primes: float,
                      active_only: bool = True) -> List[Dict[str, Any]]:
    """Calculate all active deductions from gross + allowances."""
    retenues_rules = db.get_all_retenues(active_only=active_only)
    base_imposable = salaire_brut + total_primes
    result = []

    for rule in retenues_rules:
        nom = rule["nom_retenue"]
        calc_type = rule["type_calcul"]
        valeur = rule["valeur"]

        if calc_type == "fixe":
            montant = valeur
        elif calc_type == "pourcentage":
            montant = base_imposable * valeur
        else:
            montant = 0

        result.append({
            "id_retenue": rule["id_retenue"],
            "nom_retenue": nom,
            "type_calcul": calc_type,
            "valeur": valeur,
            "montant": round(montant, 2),
        })

    return result


def calculer_salaire_complet(emp_id: int, month: str) -> Optional[Dict[str, Any]]:
    """
    Complete salary calculation for one employee for a given month.
    Returns a dictionary with all salary components.
    """
    employe = db.get_employe_by_id(emp_id)
    if not employe or employe["statut"] != "actif":
        return None

    # 1. Base salary from grade + echelon
    salaire_base = calculer_salaire_base(employe["code_grade"], employe["id_echelon"])

    # 2. Allowances (primes)
    primes = calculer_primes(
        salaire_base,
        employe["nombre_enfants"],
        employe["date_embauche"]
    )
    total_primes = sum(p["montant"] for p in primes)

    # 3. Gross salary
    salaire_brut = salaire_base

    # 4. Deductions (retenues)
    retenues = calculer_retenues(salaire_brut, total_primes)
    total_retenues = sum(r["montant"] for r in retenues)

    # 5. Net salary
    salaire_net = salaire_brut + total_primes - total_retenues

    # 6. Years of service
    anciennete = calculer_anciennete(employe["date_embauche"])

    return {
        "id_employe": emp_id,
        "employe_nom": employe["nom"],
        "poste": employe["poste"],
        "code_grade": employe["code_grade"],
        "numero_echelon": employe["numero_echelon"],
        "mois": month,
        "salaire_base": round(salaire_base, 2),
        "salaire_brut": round(salaire_brut, 2),
        "primes": primes,
        "total_primes": round(total_primes, 2),
        "retenues": retenues,
        "total_retenues": round(total_retenues, 2),
        "salaire_net": round(salaire_net, 2),
        "anciennete": anciennete,
        "nombre_enfants": employe["nombre_enfants"],
    }


def traiter_paie_mensuelle(month: str) -> Dict[str, Any]:
    """
    Process payroll for all active employees for a given month.
    Returns summary statistics.
    """
    employes = db.get_all_employes()
    results = {
        "month": month,
        "total_processed": 0,
        "total_failed": 0,
        "total_brut": 0,
        "total_primes": 0,
        "total_retenues": 0,
        "total_net": 0,
        "details": [],
    }

    for emp in employes:
        if emp["statut"] != "actif":
            continue

        calc = calculer_salaire_complet(emp["id_employe"], month)
        if calc is None:
            results["total_failed"] += 1
            continue

        # Save to database
        paie_id = db.create_paie(
            emp["id_employe"],
            month,
            calc["salaire_brut"],
            calc["total_primes"],
            calc["total_retenues"],
            calc["salaire_net"]
        )

        # Save prime details
        for p in calc["primes"]:
            db.save_paie_prime(paie_id, p["id_prime"], p["montant"])

        # Save retenue details
        for r in calc["retenues"]:
            db.save_paie_retenue(paie_id, r["id_retenue"], r["montant"])

        results["total_processed"] += 1
        results["total_brut"] += calc["salaire_brut"]
        results["total_primes"] += calc["total_primes"]
        results["total_retenues"] += calc["total_retenues"]
        results["total_net"] += calc["salaire_net"]
        results["details"].append(calc)

    return results
