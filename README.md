<<<<<<< HEAD
# energy_tracker
=======
# 🌿 Renewable Energy Usage Tracker
**A Full-Stack Web Application for Clean Energy Telemetry, Analytics, and Environmental Accounting**

---

## 📌 1. Project Overview
The **Renewable Energy Usage Tracker** is a full-stack web application engineered to record, manage, analyze, and optimize renewable energy generation and consumption. Designed as a college project and enterprise-grade telemetry solution, it empowers users to monitor clean energy adoption across multiple sources (Solar, Wind, Hydro, Biomass, Geothermal, and Other Renewables), evaluate carbon footprint offsets, track financial electricity savings, and achieve sustainability targets.

---

## 🎯 2. Core Problem & Architecture Philosophy

### The Data Independence Principle
In many legacy systems, daily energy logs are naively overwritten or merged upon input. This system enforces strict **Record Independence**:
* Every single meter reading or micro-generator entry is stored as an **independent database row**.
* Users can log unlimited records for:
  * Different sources on the same date.
  * The same source multiple times on the same date (e.g. Morning solar vs. Afternoon bifacial array).
  * Different sources across various dates.
* **No Unique Constraint on `(user_id, date)` or `(user_id, date, source)`** exists in the database schema.
* All source-wise, date-wise, and combined aggregations are calculated **dynamically on query** by backend services, ensuring raw historical data remains completely unaltered.

---

## ✨ 3. Key Features

1. **Authentication & User Isolation**:
   * Login as the mandatory first screen.
   * Secure password hashing with Werkzeug.
   * Stateless JWT authentication with Flask-JWT-Extended.
   * Strict user tenancy: each authenticated user accesses only their own records.
2. **Energy Record CRUD with Multi-Entry Support**:
   * Create, Read, Update, and Delete operations over MySQL.
   * Special **"Save & Add Another"** workflow for rapid same-date multi-source data logging.
3. **Comprehensive Aggregation Engine**:
   * **Individual View**: Inspect raw telemetry rows.
   * **Source-Wise Aggregation**: Filter by Solar, Wind, Hydro, Biomass, Geothermal, or Other.
   * **Date-Wise & Date-Range Aggregation**: Today, Yesterday, This Week, This Month, This Year, or Custom Ranges.
   * **Combined View**: Aggregate telemetry across all renewable sources.
4. **Calculations & Environmental Accounting**:
   * **Renewable Energy Share (%)**: $\frac{\text{Renewable Consumed}}{\text{Total Consumed}} \times 100$
   * **Estimated CO2 Avoided (kg)**: $\text{Renewable Consumed} \times \text{Grid Emission Factor (0.82 kg/kWh)}$
   * **Estimated Grid Displaced (kWh)**: Direct displacement of fossil grid electricity.
   * **Estimated Cost Savings ($)**: $\text{Renewable Consumed} \times \text{Electricity Tariff}$
5. **Interactive Visual Analytics**:
   * Chart.js visualizations for generation trends, renewable vs. grid consumption stacks, source contribution doughnuts, and dual-axis CO2/savings timelines.
6. **Renewable Goals Management**:
   * Set targets for Generation, Consumption, Renewable %, CO2 Avoidance, Grid Displacement, or Cost Savings.
   * Real-time progress bars, percentage completion, and status lifecycles (Active, Completed, Expired).
7. **Smart Data-Driven Insights**:
   * Rule-based analytical engine highlighting top producing sources, month-over-month growth, milestone achievements, and optimization opportunities.
8. **CSV Telemetry Export**:
   * Download personal telemetry logs formatted with all calculated indicators.
9. **Dual-Mode Operation (Live API + Standalone Demo Mode)**:
   * Supports live communication with MySQL & Flask REST API.
   * Seamless client-side **Demo Mode** for offline presentation and interactive grading without requiring a live database server.

---

## 🛠️ 4. Technology Stack

* **Frontend**: HTML5, Vanilla CSS3 (Custom Design System, Light/Dark theme), Vanilla JavaScript (ES6+ Modules), Chart.js (CDN), Fetch API.
* **Backend**: Python 3.12+, Flask 3.x, Flask-SQLAlchemy 3.x, Flask-JWT-Extended, Flask-CORS, Werkzeug.
* **Database**: MySQL 8.x (via PyMySQL) with automated local dev SQLite fallback.
* **Testing**: Pytest with automated acceptance scenario testing.

---

## 🗄️ 5. Database Schema

The database schema is defined in [`database/schema.sql`](file:///database/schema.sql):

```
+-------------------------------------------------------+
|                         users                         |
|-------------------------------------------------------|
| id (PK) | full_name | email (UQ) | password_hash      |
| created_at | updated_at                               |
+-------------------------------------------------------+
                           | 1:N
       +-------------------+-------------------+
       |                   |                   |
+------------------+ +------------------+ +------------------+
|  energy_records  | |      goals       | |    activities    |
|------------------| |------------------| |------------------|
| id (PK)          | | id (PK)          | | id (PK)          |
| user_id (FK)     | | user_id (FK)     | | user_id (FK)     |
| date             | | goal_type        | | action_type      |
| renewable_source | | target_value     | | description      |
| energy_gen_kwh   | | start_date       | | timestamp        |
| ren_con_kwh      | | end_date         | +------------------+
| grid_con_kwh     | | status           |
| total_con_kwh    | +------------------+
| tariff           |
| notes            |
+------------------+
```

---

## 🚀 6. Setup & Installation Instructions

### Prerequisites
* Python 3.10 or higher
* MySQL Server (Optional for local dev, fallback SQLite is built-in)

### Step 1: Clone or Navigate to Project Directory
```powershell
cd "c:\Users\DELL\Desktop\Renewable Energy Usage Tracker"
```

### Step 2: Create & Activate Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
pip install -r backend/requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
If using MySQL, configure your MySQL credentials in `.env`:
```env
DATABASE_URL=mysql+pymysql://root:your_mysql_password@localhost:3306/renewable_energy_db
```
To initialize MySQL tables:
```sql
CREATE DATABASE IF NOT EXISTS renewable_energy_db;
-- Import schema:
-- mysql -u root -p renewable_energy_db < database/schema.sql
```

---

## 🏃 7. Running the Application

### Option A: Full-Stack Flask Web Server (Recommended)
Start the Flask application (which hosts both REST APIs and frontend assets):
```powershell
python -m backend.app
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### Option B: Frontend Live Server
If serving the frontend separately via VS Code Live Server or python HTTP server:
```powershell
python -m http.server 3000 --directory frontend
```
Navigate to:
```
http://127.0.0.1:3000/index.html
```

---

## 🧪 8. Automated Testing & Exact Acceptance Scenario

The project includes an automated test suite verifying the multi-source same-date scenario specified in the system requirements.

To run tests:
```powershell
python -m pytest -v
```

### Verified Acceptance Scenario:
1. **August 18 Entries**:
   * Solar $\rightarrow$ 10 kWh
   * Solar $\rightarrow$ 5 kWh
   * Wind $\rightarrow$ 10 kWh
   * Biomass $\rightarrow$ 10 kWh
   * Hydro $\rightarrow$ 10 kWh
   * Geothermal $\rightarrow$ 10 kWh
   * **Verification**: Exactly 6 independent database records created.
   * Solar Total = $10 + 5 = 15\text{ kWh}$
   * August 18 Combined Generation = $55\text{ kWh}$
2. **August 19 Entries**:
   * Solar $\rightarrow$ 20 kWh
   * Wind $\rightarrow$ 15 kWh
   * **Verification**: August 19 Total = $35\text{ kWh}$
3. **Combined 18–19 August**:
   * Total Combined = $55 + 35 = 90\text{ kWh}$
   * Solar Filter Total = $35\text{ kWh}$
   * Wind Filter Total = $25\text{ kWh}$
   * All original records remain intact and separate.

---

## 📚 9. REST API Reference

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/register` | Register new user account | No |
| `POST` | `/api/auth/login` | Authenticate user & receive JWT | No |
| `GET` | `/api/auth/me` | Fetch authenticated profile | Yes |
| `POST` | `/api/auth/logout` | Log out session | Yes |
| `GET` | `/api/energy` | Filtered & paginated energy records | Yes |
| `POST` | `/api/energy` | Create independent energy record | Yes |
| `GET` | `/api/energy/<id>` | Fetch single record with metrics | Yes |
| `PUT` | `/api/energy/<id>` | Update energy record | Yes |
| `DELETE` | `/api/energy/<id>` | Delete energy record | Yes |
| `GET` | `/api/energy/export/csv` | Export records to CSV file | Yes |
| `GET` | `/api/dashboard/stats` | KPI statistics & aggregated summaries | Yes |
| `GET` | `/api/dashboard/recent` | Recent entries, activity log, insights | Yes |
| `GET` | `/api/analytics/overview` | Time-series data for trends | Yes |
| `GET` | `/api/analytics/sources` | Source comparison matrices | Yes |
| `GET` | `/api/analytics/environmental` | Carbon avoidance & equivalencies | Yes |
| `GET` | `/api/analytics/savings` | Cost savings & tariff breakdown | Yes |
| `GET` | `/api/analytics/insights` | Rule-based data-driven insights | Yes |
| `GET` | `/api/goals` | Goals list with live progress | Yes |
| `POST` | `/api/goals` | Create sustainability goal | Yes |
| `PUT` | `/api/goals/<id>` | Update goal | Yes |
| `DELETE` | `/api/goals/<id>` | Delete goal | Yes |
| `GET` | `/api/activities` | Audit trail history | Yes |
| `GET` | `/api/settings` | Retrieve user preferences | Yes |
| `PUT` | `/api/settings` | Update calculation constants & theme | Yes |
| `PUT` | `/api/settings/profile` | Update profile information | Yes |

---

## 🌟 10. Demo Credentials
* **Email**: `alex@example.com`
* **Password**: `Password123!`

---

## 🔮 11. Future Scope
* Integration of real IoT smart meter WebSockets for automated live inverter polling.
* Machine Learning predictive models for solar irradiance and wind velocity forecasting.
* Multi-tariff Time-Of-Use (TOU) and net metering tariff schedules.
* Export to PDF environmental compliance audit reports.
>>>>>>> e17499a (Upload project)
