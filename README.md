# Salary Management System - State Administration

## Systeme de Gestion des Salaires - Administration de l'Etat

A complete Streamlit-based salary management system for state administrative bodies, featuring employee CRUD, salary calculation with allowances/deductions, monthly payroll processing, payslip generation, and role-based access control.

---

## Features (F1-F12)

| ID | Feature | Description |
|----|---------|-------------|
| F1 | Employee Management | Full CRUD: name, grade, step, hire date, bank account, position |
| F2 | Grade & Salary Scale | Define grades (A1, A2, B1...) with base salary per step |
| F3 | Basic Salary Calculation | Auto-compute gross salary from grade and step |
| F4 | Allowances | Family allowance, residence supplement, seniority bonus |
| F5 | Deductions | Social security (CNAS), retirement (CNR), income tax (IRG) |
| F6 | Net Salary Calculation | Gross + allowances - deductions |
| F7 | Monthly Payroll Processing | Generate salaries for all employees for a given month |
| F8 | Individual Payslip | View/print detailed payslip (styled HTML) |
| F9 | Bulk Import/Export | Import employees from CSV, export payroll to Excel |
| F10 | Salary History | Track each employee's salary month by month |
| F11 | Admin Dashboard | Summary metrics, charts, and visual analytics |
| F12 | Role-based Login | Admin (full access) vs Employee (view own payslip only) |

---

## How to Run

### Method 1: Quick Start (Recommended)

```bash
# 1. Navigate to the project folder
cd salary_management

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
streamlit run app.py

# 4. Open your browser at: http://localhost:8502
```

### Method 2: Using a Virtual Environment

```bash
# 1. Navigate to the project folder
cd salary_management

# 2. Create a virtual environment
python -m venv venv

# 3. Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
streamlit run app.py

# 6. Open your browser at: http://localhost:8502
```

### Method 3: Using Conda

```bash
# 1. Navigate to the project folder
cd salary_management

# 2. Create a conda environment
conda create -n salary_env python=3.11

# 3. Activate it
conda activate salary_env

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
streamlit run app.py
```

---

## Default Login Credentials

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Administrator (full access) |

> To create employee accounts, go to **Employees** > Add Employee, then create a user account linked to that employee.

---

## Application Structure

```
salary_management/
├── app.py                   # Main Streamlit application
├── database.py             # Database operations (SQLite)
├── auth.py                 # Authentication & session management
├── salary_engine.py        # Salary calculation engine
├── payslip.py             # Payslip HTML generation
├── requirements.txt       # Python dependencies
├── .streamlit/
│   └── config.toml        # Streamlit UI configuration
└── README.md              # This file
```

---

## Technology Stack

- **Frontend**: Streamlit (Python web framework)
- **Database**: SQLite (file-based, no server needed)
- **Authentication**: Werkzeug password hashing + session state
- **Charts**: Plotly (interactive visualizations)
- **Data Export**: Pandas + XlsxWriter (Excel files)
- **Data Import**: Pandas (CSV parsing)

---

## Database Schema

### Tables:
- `grade` - Salary scales per grade code
- `echelon` - Step definitions with coefficients
- `employe` - Employee records
- `prime` - Allowance types and rules
- `retenue` - Deduction types and rules
- `utilisateur` - Login accounts
- `paie` - Payroll records per employee per month
- `paie_prime` - Junction: payroll allowances
- `paie_retenue` - Junction: payroll deductions

---

## Salary Calculation Formula

```
Base Salary = grade_base + (echelon - 1) * increment

Allowances:
  - Family allowance = per_child_amount * number_of_children
  - Residence = base_salary * percentage
  - Seniority = base_salary * percentage * years_of_service

Deductions (applied on Base + Allowances):
  - CNAS = 9% (Social Security)
  - CNR = 6.5% (Retirement)
  - IRG = 5% (Income Tax)

Net Salary = Base Salary + Allowances - Deductions
```

---

## Pre-loaded Data

The system comes with:
- **9 grades** (A1 through D2) with realistic Algerian public sector salary bases
- **12 echelons** (steps 1-12) with progressive coefficients
- **5 allowance types**: family, residence, seniority, transport, meal
- **4 deduction types**: CNAS, CNR, IRG, health insurance
- **1 admin account** for immediate login

---

## Notes

- The database (`salary_db.sqlite`) is auto-created on first run
- All salary calculations use the Algerian public administration model
- Payslips are generated as styled HTML (printable via browser)
- The app runs locally on port 8502 by default
