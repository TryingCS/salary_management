"""
payslip.py - Payslip (Bulletin de Paie) generation in HTML format.
Generates styled, printable payslip HTML for a given payroll record.
"""

from datetime import datetime
import database as db


def generate_payslip_html(paie_id: int) -> str:
    """Generate a styled HTML payslip for the given payroll record."""
    paie = db.get_paie_details(paie_id)
    if not paie:
        return "<p>Error: Payroll record not found.</p>"

    primes = db.get_primes_for_paie(paie_id)
    retenues = db.get_retenues_for_paie(paie_id)

    mois_str = datetime.strptime(paie["mois"], "%Y-%m-%d").strftime("%B %Y").capitalize()

    primes_rows = ""
    for p in primes:
        primes_rows += f"""
            <tr>
                <td style="padding: 6px 10px; border-bottom: 1px solid #ddd;">{p['nom_prime'].replace('_', ' ').title()}</td>
                <td style="padding: 6px 10px; border-bottom: 1px solid #ddd; text-align: right;">{p['montant_applique']:,.2f} DA</td>
            </tr>
        """

    retenues_rows = ""
    for r in retenues:
        retenues_rows += f"""
            <tr>
                <td style="padding: 6px 10px; border-bottom: 1px solid #ddd;">{r['nom_retenue'].replace('_', ' ').upper()}</td>
                <td style="padding: 6px 10px; border-bottom: 1px solid #ddd; text-align: right; color: #E74C3C;">-{r['montant_retenu']:,.2f} DA</td>
            </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Bulletin de Paie - {paie['nom']} - {mois_str}</title>
        <style>
            @media print {{
                body {{ margin: 0; }}
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background: #F4F6F7; margin: 0; padding: 20px;">
        <div style="max-width: 800px; margin: 0 auto; background: #FFFFFF; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">

            <!-- Header -->
            <div style="background: #2C3E50; color: white; padding: 25px; text-align: center;">
                <h1 style="margin: 0; font-size: 1.5em;">🏛 REPUBLIQUE ALGERIENNE DEMOCRATIQUE ET POPULAIRE</h1>
                <h2 style="margin: 10px 0 0; font-size: 1.2em; font-weight: normal;">BULLETIN DE PAIE</h2>
            </div>

            <!-- Employee Info -->
            <div style="padding: 25px; border-bottom: 3px solid #E67E22;">
                <table style="width: 100%; font-size: 0.95em;">
                    <tr>
                        <td style="padding: 4px 0;"><strong>Nom et Prenom:</strong> {paie['nom']}</td>
                        <td style="padding: 4px 0; text-align: right;"><strong>Periode:</strong> {mois_str}</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0;"><strong>Poste:</strong> {paie['poste'] or 'Non defini'}</td>
                        <td style="padding: 4px 0; text-align: right;"><strong>Grade:</strong> {paie['code_grade']} | <strong>Echelon:</strong> {paie['numero_echelon']}</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0;"><strong>Compte Bancaire:</strong> {paie['compte_bancaire'] or 'N/A'}</td>
                        <td style="padding: 4px 0; text-align: right;"><strong>Date de generation:</strong> {datetime.now().strftime('%d/%m/%Y')}</td>
                    </tr>
                </table>
            </div>

            <div style="padding: 25px;">
                <!-- Salary Summary -->
                <div style="display: flex; gap: 15px; margin-bottom: 25px;">
                    <div style="flex: 1; background: #EBF5FB; padding: 15px; border-radius: 8px; text-align: center;">
                        <p style="color: #7F8C8D; margin: 0; font-size: 0.85em;">SALAIRE DE BASE</p>
                        <p style="color: #2C3E50; font-size: 1.3em; font-weight: bold; margin: 5px 0;">{paie['salaire_base']:,.2f} DA</p>
                    </div>
                    <div style="flex: 1; background: #EAFAF1; padding: 15px; border-radius: 8px; text-align: center;">
                        <p style="color: #27AE60; margin: 0; font-size: 0.85em;">TOTAL PRIMES</p>
                        <p style="color: #27AE60; font-size: 1.3em; font-weight: bold; margin: 5px 0;">+{paie['total_primes']:,.2f} DA</p>
                    </div>
                    <div style="flex: 1; background: #FADBD8; padding: 15px; border-radius: 8px; text-align: center;">
                        <p style="color: #E74C3C; margin: 0; font-size: 0.85em;">TOTAL RETENUES</p>
                        <p style="color: #E74C3C; font-size: 1.3em; font-weight: bold; margin: 5px 0;">-{paie['total_retenues']:,.2f} DA</p>
                    </div>
                </div>

                <!-- Details -->
                <div style="display: flex; gap: 25px;">
                    <!-- Primes -->
                    <div style="flex: 1;">
                        <h3 style="color: #27AE60; border-bottom: 2px solid #27AE60; padding-bottom: 8px; margin-bottom: 10px;">✚ PRIMES ET INDEMNITES</h3>
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">
                            <thead>
                                <tr style="background: #F4F6F7;">
                                    <th style="padding: 8px 10px; text-align: left; border-bottom: 2px solid #ddd;">Libelle</th>
                                    <th style="padding: 8px 10px; text-align: right; border-bottom: 2px solid #ddd;">Montant</th>
                                </tr>
                            </thead>
                            <tbody>
                                {primes_rows if primes_rows else '<tr><td colspan="2" style="padding: 10px; text-align: center; color: #7F8C8D;">Aucune prime</td></tr>'}
                                <tr style="background: #EAFAF1; font-weight: bold;">
                                    <td style="padding: 10px; border-top: 2px solid #27AE60;">TOTAL PRIMES</td>
                                    <td style="padding: 10px; text-align: right; border-top: 2px solid #27AE60;">{paie['total_primes']:,.2f} DA</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <!-- Retenues -->
                    <div style="flex: 1;">
                        <h3 style="color: #E74C3C; border-bottom: 2px solid #E74C3C; padding-bottom: 8px; margin-bottom: 10px;">✕ RETENUES ET COTISATIONS</h3>
                        <table style="width: 100%; border-collapse: collapse; font-size: 0.9em;">
                            <thead>
                                <tr style="background: #F4F6F7;">
                                    <th style="padding: 8px 10px; text-align: left; border-bottom: 2px solid #ddd;">Libelle</th>
                                    <th style="padding: 8px 10px; text-align: right; border-bottom: 2px solid #ddd;">Montant</th>
                                </tr>
                            </thead>
                            <tbody>
                                {retenues_rows if retenues_rows else '<tr><td colspan="2" style="padding: 10px; text-align: center; color: #7F8C8D;">Aucune retenue</td></tr>'}
                                <tr style="background: #FADBD8; font-weight: bold;">
                                    <td style="padding: 10px; border-top: 2px solid #E74C3C;">TOTAL RETENUES</td>
                                    <td style="padding: 10px; text-align: right; border-top: 2px solid #E74C3C;">{paie['total_retenues']:,.2f} DA</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Net Salary -->
                <div style="margin-top: 25px; background: #2C3E50; color: white; padding: 20px; border-radius: 8px; text-align: center;">
                    <p style="margin: 0; font-size: 0.9em; color: #BDC3C7;">SALAIRE NET A PAYER</p>
                    <p style="margin: 5px 0 0; font-size: 2em; font-weight: bold;">{paie['salaire_net']:,.2f} DA</p>
                </div>

                <!-- Footer -->
                <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #BDC3C7; font-size: 0.8em; color: #7F8C8D; text-align: center;">
                    <p>Ce document est genere electroniquement par le systeme de gestion des salaires.</p>
                    <p>Etat: <strong>{paie['statut'].upper()}</strong></p>
                </div>
            </div>
        </div>

        <div class="no-print" style="text-align: center; margin-top: 20px;">
            <button onclick="window.print()" style="background: #E67E22; color: white; border: none; padding: 12px 30px; font-size: 1em; border-radius: 5px; cursor: pointer;">
                🖨 Imprimer le Bulletin
            </button>
        </div>
    </body>
    </html>
    """
    return html


def generate_payslip_summary_card(paie: dict) -> str:
    """Generate a compact HTML card for a payslip preview."""
    mois_str = datetime.strptime(paie["mois"], "%Y-%m-%d").strftime("%B %Y").capitalize()

    statut_color = {"en_attente": "#F39C12", "traite": "#3498DB", "paye": "#27AE60"}
    color = statut_color.get(paie["statut"], "#7F8C8D")

    html = f"""
    <div style="background: #FFFFFF; border-radius: 10px; padding: 20px; margin: 10px 0;
                box-shadow: 0 2px 5px rgba(0,0,0,0.08); border-left: 4px solid {color};">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h4 style="margin: 0; color: #2C3E50;">{paie.get('nom', 'Employe')}</h4>
                <p style="margin: 4px 0; color: #7F8C8D; font-size: 0.9em;">{paie.get('poste', '')} | Grade: {paie.get('code_grade', 'N/A')}</p>
            </div>
            <div style="text-align: right;">
                <p style="margin: 0; color: {color}; font-weight: bold; font-size: 0.85em;">{paie['statut'].upper()}</p>
                <p style="margin: 4px 0; color: #7F8C8D; font-size: 0.85em;">{mois_str}</p>
            </div>
        </div>
        <div style="display: flex; gap: 15px; margin-top: 15px;">
            <div style="flex: 1; text-align: center; background: #EBF5FB; padding: 10px; border-radius: 6px;">
                <p style="margin: 0; font-size: 0.75em; color: #7F8C8D;">BRUT</p>
                <p style="margin: 0; font-weight: bold; color: #2C3E50;">{paie['salaire_brut']:,.0f} DA</p>
            </div>
            <div style="flex: 1; text-align: center; background: #EAFAF1; padding: 10px; border-radius: 6px;">
                <p style="margin: 0; font-size: 0.75em; color: #27AE60;">PRIMES</p>
                <p style="margin: 0; font-weight: bold; color: #27AE60;">+{paie['total_primes']:,.0f} DA</p>
            </div>
            <div style="flex: 1; text-align: center; background: #FADBD8; padding: 10px; border-radius: 6px;">
                <p style="margin: 0; font-size: 0.75em; color: #E74C3C;">RETENUES</p>
                <p style="margin: 0; font-weight: bold; color: #E74C3C;">-{paie['total_retenues']:,.0f} DA</p>
            </div>
            <div style="flex: 1; text-align: center; background: #2C3E50; padding: 10px; border-radius: 6px;">
                <p style="margin: 0; font-size: 0.75em; color: #BDC3C7;">NET</p>
                <p style="margin: 0; font-weight: bold; color: #FFFFFF;">{paie['salaire_net']:,.0f} DA</p>
            </div>
        </div>
    </div>
    """
    return html
