# NeuraQuery-AI
Autonomous On-Device Natural Language to SQL &amp; Excel Intelligence (100% Air-Gapped SLM)
# ⚡ NeuraQuery AI — Autonomous On-Device Data Intelligence

**JG TECHVERSE 2026 | Arena: Buddhi (Small Language Model Challenge)**

NeuraQuery is a 100% air-gapped, on-device AI data copilot that translates plain English questions into verified, executable SQLite queries across Microsoft Excel (`.xlsx`), CSV, and `.db` databases—running entirely on standard laptop CPUs with **zero cloud API costs** and **zero data leakage**.

---

## 1. What the Project Does
* **Natural Language to SQL:** Converts plain-English business, academic, and healthcare questions into deterministic SQLite `SELECT` queries in **<1 second**.
* **Universal File Ingestion:** Drag-and-drop support for `.xlsx`, `.xls`, `.csv`, and `.db` files via an in-memory SQLite virtualization engine (`:memory:`).
* **Autonomous Self-Healing Loop:** Automatically intercepts runtime SQL exceptions (such as column typos), passes the traceback and active schema back to the SLM, and auto-corrects the query in **<0.5 seconds**.
* **AST Security Guardrails:** Blocks destructive commands (`DROP`, `DELETE`, `UPDATE`, `ALTER`, `TRUNCATE`) prior to execution.
* **3-Tier Commercial Workspace:** Includes Community (Free), Pro (`PRO2026` — Live Spreadsheet Editor, Automated Bar Charts, CSV Export), and Enterprise (`ENT-9999` — DPDP Act 2023 Compliance Audit Trail).

---

## 2. How to Run It (100% Offline Setup)

### A. Clone the Repository & Install Dependencies
```bash
git clone [https://github.com/YOUR-USERNAME/NeuraQuery-AI.git](https://github.com/YOUR-USERNAME/NeuraQuery-AI.git)
cd NeuraQuery-AI
pip install llama-cpp-python --extra-index-url [https://abetlen.github.io/llama-cpp-python/whl/cpu](https://abetlen.github.io/llama-cpp-python/whl/cpu)
pip install -r requirements.txt
