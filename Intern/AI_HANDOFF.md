# AI Handoff - Vessel Laycan & Demurrage Calculator

This document serves as a complete handoff for the **Vessel Laycan & Demurrage Calculator** project inside the `Intern` folder. It outlines the project's features, architecture, database schemas, shipping rules, and instructions for developers or subsequent AI agents.

---

## 1. Project Overview
The application is a standalone shipping demurrage and laytime calculator tool. It calculates:
1. **Laytime Start Time**: Determined automatically using specific harbor rules based on arrival window (Laycan), berth type, arrival time, and Notice of Readiness (NOR) tender/acceptance times.
2. **Operational Time**: Net time spent discharging, after accounting for shifting deductions and netted vessel-side delays.
3. **Delay Netting**: Netted delay offsets (Vessel Delays vs. Terminal Delays) to determine the net deduction.
4. **Demurrage Status**: Displays whether demurrage is payable, the total payable hours, and a full calculation sheet.

---

## 2. Technology Stack & Design System
* **Backend**: Python 3.9 + FastAPI for lightweight REST APIs.
* **Database**: SQLite3 for persistent user accounts, session tokens, and calculation history.
* **Frontend**: HTML5 + Vanilla JS + CSS styled according to the **IBM Carbon Design System** (g100 theme, sharp corners, flat borders, `#0f62fe` accent colors, and `IBM Plex Sans` typography).
* **Containerization**: Dockerized setup supporting environment configurations via a `.env` file.

---

## 3. Codebase Structure
All code is self-contained in the `Intern` directory:

* [calculator.py](file:///Users/nushan/Projects/Anjalee/Intern/calculator.py): Core mathematical formulas, time differences, and rules decision logic.
* [db.py](file:///Users/nushan/Projects/Anjalee/Intern/db.py): SQLite database tables, session validation, user registration, history saving, and `.env` credentials loading.
* [main.py](file:///Users/nushan/Projects/Anjalee/Intern/main.py): FastAPI routing endpoints, cookies/token auth dependencies, and static files mount.
* [test_calculator.py](file:///Users/nushan/Projects/Anjalee/Intern/test_calculator.py): Pytest unit tests for laycan calculation start rules.
* [test_db.py](file:///Users/nushan/Projects/Anjalee/Intern/test_db.py): Pytest unit tests for database seeding, sessions, and CRUD operations.
* [static/index.html](file:///Users/nushan/Projects/Anjalee/Intern/static/index.html): HTML structure layout divided into tabbed inputs, active results, history, and admin forms.
* [static/style.css](file:///Users/nushan/Projects/Anjalee/Intern/static/style.css): Carbon UI style sheet.
* [static/app.js](file:///Users/nushan/Projects/Anjalee/Intern/static/app.js): DOM manipulation, state arrays for delays, and REST endpoints integration.
* [Dockerfile](file:///Users/nushan/Projects/Anjalee/Intern/Dockerfile): Docker image instructions.
* [requirements.txt](file:///Users/nushan/Projects/Anjalee/Intern/requirements.txt): Python dependencies.
* [.env](file:///Users/nushan/Projects/Anjalee/Intern/.env): Environment variables configuration for default admin credentials.

---

## 4. Shipping Rules & Logic

### Laytime Start Time Determination
Let $T_{arr}$ be the arrival time, $D_{arr}$ be the arrival date, $W_{start}$ and $W_{end}$ be the laycan date window, and $T_{acc}$ be the NOR Accepted time.

1. **Before Laycan Window ($D_{arr} < W_{start}$)**:
   * If terminal requests early start: Start = $T_{acc}$.
   * Else:
     * **DTB**: Start = $W_{start}$ at 13:00.
     * **SPBM**: Start = $W_{start}$ at 12:00.
2. **During Laycan Window ($W_{start} \le D_{arr} \le W_{end}$)**:
   * **DTB** (Cutoff 17:00):
     * If $T_{arr} \le$ 17:00: Start = $T_{acc}$.
     * If $T_{arr} >$ 17:00:
       * If terminal grants late permission: Start = $T_{acc}$.
       * Else: Start = Next Day ($D_{arr} + 1$) at 13:00.
   * **SPBM** (Cutoff 15:00):
     * If $T_{arr} \le$ 15:00: Start = $T_{acc}$.
     * If $T_{arr} >$ 15:00:
       * If terminal grants late permission: Start = $T_{acc}$.
       * Else: Start = Next Day ($D_{arr} + 1$) at 12:00.
3. **After Laycan Window ($D_{arr} > W_{end}$)**:
   * Start = $T_{acc}$.

### Allowed Laytime Hours
* Finished Product (Petrol, Diesel, JetA1): **96 hours**.
* Crude Vessel: **72 hours**.
* Fuel Oil: **120 hours**.

### Shifting Deduction ("shifty")
* If the vessel berths 2 or more times, a shifting allowance of **4.0 hours** is deducted from the operational time.

### Delay Netting Formula
Let $D_v$ be the total vessel delays, and $D_t$ be the total terminal delays.
* $\text{Net Vessel Delay} = \max(0, D_v - D_t)$
* $\text{Net Terminal Delay} = \max(0, D_t - D_v)$
* Operational Time is calculated as:
  $$\text{Operational Time} = \text{Actual Elapsed Time} - \text{Shifting Deduction} - \text{Net Vessel Delay}$$
* Demurrage hours:
  $$\text{Demurrage Hours} = \max(0, \text{Operational Time} - \text{Allowed Laytime})$$

---

## 5. Security & Session Auth
* Passwords are saved with PBKDF2 (HMAC-SHA256, 100,000 iterations, 16-byte random salt).
* Secure HTTP-only cookies are used for web sessions, falling back to Bearer headers for API requests.
* **Role Authorization**:
  * `admin` role can manage user accounts (creating/deleting users), view all calculations history, and perform calculations.
  * `user` role can perform calculations and view/delete their own history.

---

## 6. How to Deploy & Verify

### Run locally
```bash
# 1. Install dependencies
.venv/bin/pip install -r Intern/requirements.txt

# 2. Run server
.venv/bin/uvicorn Intern.main:app --port 8000 --reload
```

### Run tests
```bash
PYTHONPATH=. .venv/bin/pytest Intern/
```

### Run inside Docker
```bash
cd Intern
docker build -t demurrage-calc .
docker run -d -p 8000:8000 --env-file .env --name demurrage-app demurrage-calc
```
Default credentials will seed from `Intern/.env`.
