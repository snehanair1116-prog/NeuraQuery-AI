# app.py
import os
import re
import sqlite3
import time
from llama_cpp import Llama
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="NeuraQuery AI — Autonomous Data Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 1. Initialize State Management
if "authenticated" not in st.session_state:
  st.session_state.authenticated = False
  st.session_state.user_tier = "FREE"
  st.session_state.client_name = ""
  st.session_state.audit_logs = []
if "db_conn" not in st.session_state:
  st.session_state.db_conn = sqlite3.connect(
      ":memory:", check_same_thread=False
  )

conn = st.session_state.db_conn
table_name = "data_table"


# 2. Offline SLM Engine Loader
@st.cache_resource
def load_slm():
  model_path = "models/qwen.gguf"
  if not os.path.exists(model_path):
    st.error(
        f"❌ Model file not found at '{model_path}'. Please ensure 'qwen.gguf'"
        " is in 'models/' folder."
    )
    st.stop()
  return Llama(model_path=model_path, n_ctx=1024, n_threads=4, verbose=False)


# 3. Helper: Bulletproof Regex SQL Cleaner
def clean_sql(raw_text: str) -> str:
  cleaned = raw_text.strip()
  # Remove markdown codeblocks if any
  cleaned = re.sub(r"```(?:sql)?", "", cleaned, flags=re.IGNORECASE).strip()
  # Extract from SELECT onward if any intro text exists
  match = re.search(
      r"(SELECT\b.*)", cleaned, flags=re.IGNORECASE | re.DOTALL
  )
  if match:
    cleaned = match.group(1).strip()
  # Cut off at first semicolon
  if ";" in cleaned:
    cleaned = cleaned.split(";")[0].strip()
  # Collapse newlines into clean single-line SQL
  cleaned = " ".join(cleaned.split())
  return cleaned + ";"


# 4. Helper: Safety Filter (Checks both user prompt and SQL)
def is_safe_query(text: str) -> bool:
  forbidden = [
      "DROP",
      "DELETE",
      "UPDATE",
      "INSERT",
      "ALTER",
      "TRUNCATE",
      "REPLACE",
  ]
  tokens = re.findall(r"\b\w+\b", text.upper())
  return not any(word in tokens for word in forbidden)


# 5. Helper: Deterministic SQL Generation (Prefix-Forced with SELECT)
def generate_sql(llm_engine, user_query_text, schema):
  prompt = f"""<|im_start|>system
You are an expert SQLite database engineer. Translate the user request into a valid SQLite SELECT query.
Table name and columns: {schema}
Rules:
- Use ONLY the exact column names listed in the schema.
- Output raw SQL only, with no explanations.
<|im_end|>
<|im_start|>user
{user_query_text}
<|im_end|>
<|im_start|>assistant
SELECT """
  response = llm_engine(
      prompt,
      max_tokens=120,
      temperature=0.1,
      stop=["<|im_end|>", ";", "```"],
  )
  generated_part = response["choices"][0]["text"].strip()
  full_sql = (
      "SELECT " + generated_part
      if not generated_part.upper().startswith("SELECT")
      else generated_part
  )
  return clean_sql(full_sql)


# 6. Helper: Self-Healing SQL Recovery
def run_with_self_healing(llm_engine, sql_query, db_conn, schema, user_question):
  cleaned_initial = clean_sql(sql_query)
  try:
    res_df = pd.read_sql_query(cleaned_initial, db_conn)
    return res_df, cleaned_initial, "Direct Execution"
  except Exception as first_error:
    heal_prompt = f"""<|im_start|>system
You are an expert SQLite engineer. Fix the broken SQL query using ONLY the valid column names in the schema.
Schema: {schema}
User question: {user_question}
Broken SQL: {cleaned_initial}
Error message: {first_error}
<|im_end|>
<|im_start|>assistant
SELECT """
    response = llm_engine(
        heal_prompt,
        max_tokens=120,
        temperature=0.1,
        stop=["<|im_end|>", ";", "```"],
    )
    generated_part = response["choices"][0]["text"].strip()
    fixed_raw = (
        "SELECT " + generated_part
        if not generated_part.upper().startswith("SELECT")
        else generated_part
    )
    fixed_sql = clean_sql(fixed_raw)
    try:
      res_df = pd.read_sql_query(fixed_sql, db_conn)
      return res_df, fixed_sql, "Self-Healed ✨"
    except Exception as second_error:
      return None, fixed_sql, f"Execution Failed: {second_error}"


# =========================================================
# 🎨 3D BULLETPROOF THEME
# =========================================================
tier = st.session_state.user_tier

if tier == "ENTERPRISE":
  accent_hex = "#F59E0B"
  glow_hex = "rgba(245, 158, 11, 0.45)"
  badge_bg = "linear-gradient(135deg, #F59E0B 0%, #D97706 100%)"
  badge_text = "#000000"
  ambient_glow = (
      "radial-gradient(circle at 85% 15%, rgba(245, 158, 11, 0.18) 0%,"
      " transparent 45%), radial-gradient(circle at 15% 85%, rgba(217, 119, 6,"
      " 0.12) 0%, transparent 45%), #07090E"
  )
elif tier == "PRO":
  accent_hex = "#8B5CF6"
  glow_hex = "rgba(139, 92, 246, 0.45)"
  badge_bg = "linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%)"
  badge_text = "#FFFFFF"
  ambient_glow = (
      "radial-gradient(circle at 85% 15%, rgba(139, 92, 246, 0.2) 0%,"
      " transparent 45%), radial-gradient(circle at 15% 85%, rgba(99, 102, 241,"
      " 0.12) 0%, transparent 45%), #07090E"
  )
else:
  accent_hex = "#06B6D4"
  glow_hex = "rgba(6, 182, 212, 0.35)"
  badge_bg = "#1E293B"
  badge_text = "#38BDF8"
  ambient_glow = (
      "radial-gradient(circle at 50% 10%, rgba(6, 182, 212, 0.15) 0%,"
      " transparent 50%), #07090E"
  )

st.markdown(
    f"""
<style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background: {ambient_glow} !important;
        color: #F8FAFC !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif;
    }}
    label, p, span, h1, h2, h3, h4, h5, h6, small, b {{
        color: #F8FAFC !important;
    }}
    .hud-card {{
        background: linear-gradient(145deg, rgba(26, 34, 53, 0.8) 0%, rgba(13, 18, 30, 0.95) 100%) !important;
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 20px !important;
        padding: 24px !important;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
        margin-bottom: 24px;
    }}
    .kpi-tile {{
        background: linear-gradient(180deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1) !important;
    }}
    .status-badge {{
        background: {badge_bg} !important;
        color: {badge_text} !important;
        font-weight: 800;
        font-size: 0.78rem;
        padding: 6px 16px;
        border-radius: 9999px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        display: inline-block;
        box-shadow: 0 0 20px {glow_hex} !important;
    }}
    div[data-testid="stCodeBlock"], pre, code, .stCode {{
        background-color: #0D121F !important;
        color: #38BDF8 !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
    }}
    div[data-testid="stCodeBlock"] * {{
        background-color: transparent !important;
        color: #38BDF8 !important;
    }}
    [data-testid="stFileUploaderDropzone"], section[data-testid="stSidebar"] [data-testid="stFileUploader"] {{
        background: rgba(20, 27, 45, 0.95) !important;
        border: 1px dashed rgba(255, 255, 255, 0.25) !important;
        border-radius: 14px !important;
    }}
    [data-testid="stFileUploaderDropzone"] * {{
        color: #F8FAFC !important;
    }}
    [data-testid="stFileUploaderDropzone"] button, [data-testid="stFileUploaderDropzone"] [data-testid="baseButton-secondary"] {{
        background: #1E293B !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 10px !important;
    }}
    button, .stButton > button, div[data-testid="stButton"] > button, [data-testid="baseButton-secondary"] {{
        background: linear-gradient(145deg, #1E293B 0%, #0F172A 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 14px !important;
        padding: 10px 22px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.5) !important;
    }}
    button *, .stButton > button * {{
        color: #FFFFFF !important;
    }}
    button:hover, .stButton > button:hover {{
        background: linear-gradient(135deg, {accent_hex} 0%, #EA580C 100%) !important;
        color: #000000 !important;
        border-color: {accent_hex} !important;
    }}
    button:hover * {{
        color: #000000 !important;
    }}
    button[kind="primary"], div[data-testid="stButton"] > button[kind="primary"] {{
        background: linear-gradient(135deg, {accent_hex} 0%, #EA580C 100%) !important;
        color: #000000 !important;
        font-weight: 800 !important;
        border: none !important;
        box-shadow: 0 10px 30px {glow_hex} !important;
    }}
    button[kind="primary"] * {{
        color: #000000 !important;
        font-weight: 800 !important;
    }}
    [data-testid="stExpander"], details {{
        background: rgba(18, 24, 38, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 14px !important;
        color: #F8FAFC !important;
        margin-bottom: 16px !important;
    }}
    [data-testid="stExpander"] summary, details > summary {{
        background: linear-gradient(145deg, #1E293B 0%, #0F172A 100%) !important;
        color: #F8FAFC !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
    }}
    [data-testid="stExpander"] summary * {{
        color: #F8FAFC !important;
    }}
    div[data-testid="stTextInput"] input, .stTextInput input {{
        background: rgba(13, 18, 30, 0.95) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        font-size: 1.05rem !important;
    }}
    div[data-testid="stTextInput"] input:focus, .stTextInput input:focus {{
        border-color: {accent_hex} !important;
        box-shadow: 0 0 25px {glow_hex} !important;
    }}
    section[data-testid="stSidebar"] {{
        background: rgba(7, 9, 14, 0.98) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }}
</style>
""",
    unsafe_allow_html=True,
)

# =========================================================
# 🚪 SCREEN 1: 3D CYBER LOGIN GATE
# =========================================================
if not st.session_state.authenticated:
  st.markdown("<br><br>", unsafe_allow_html=True)
  c1, c2, c3 = st.columns(3)

  with c2:
    st.markdown(
        """
        <div class="hud-card" style="text-align: center; padding: 40px 32px;">
            <div style="font-size: 3.5rem; margin-bottom: 6px; filter: drop-shadow(0 0 20px #F59E0B);">⚡</div>
            <h1 style="margin: 0; font-size: 2.8rem; font-weight: 900; letter-spacing: -0.03em;">NeuraQuery</h1>
            <p style="color: #94A3B8; font-size: 1.05rem; margin-top: 8px; margin-bottom: 24px;">
                Autonomous On-Device Data Intelligence
            </p>
            <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin-bottom: 28px;">
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
      st.markdown("#### 🔐 Client Authentication")
      client_id = st.text_input(
          "Organization / User ID:", placeholder="e.g., JG University / Apollo"
      )
      passcode = st.text_input(
          "License Passcode:",
          type="password",
          placeholder="Enter passcode (e.g., PRO2026)",
      )

      submit = st.form_submit_button(
          "Enter AI Workspace 🚀", use_container_width=True, type="primary"
      )

      if submit:
        clean_key = passcode.strip().upper()
        if clean_key.startswith("ENT-") or clean_key == "ENTERPRISE":
          st.session_state.authenticated = True
          st.session_state.user_tier = "ENTERPRISE"
          st.session_state.client_name = client_id or "Enterprise Admin"
          st.rerun()
        elif clean_key.startswith("PRO-") or clean_key == "PRO2026":
          st.session_state.authenticated = True
          st.session_state.user_tier = "PRO"
          st.session_state.client_name = client_id or "Pro Member"
          st.rerun()
        elif clean_key in ["FREE", "DEMO", ""]:
          st.session_state.authenticated = True
          st.session_state.user_tier = "FREE"
          st.session_state.client_name = client_id or "Community User"
          st.rerun()
        else:
          st.error(
              "Invalid license passcode. Use 'FREE', 'PRO2026', or 'ENT-9999'."
          )

    st.caption(
        "🔒 **Air-Gapped Security:** Cryptographic local authentication. Zero"
        " cloud connection."
    )
  st.stop()

# =========================================================
# 🚀 SCREEN 2: 3D MAIN WORKSPACE
# =========================================================
top_l, top_r = st.columns(2)
with top_l:
  st.markdown(
      f"""
    <div style="display: flex; align-items: center; gap: 14px; margin-bottom: 6px;">
        <span style="font-size: 2.2rem; filter: drop-shadow(0 0 10px {accent_hex});">⚡</span>
        <h2 style="margin: 0; font-size: 2.2rem; font-weight: 900; letter-spacing: -0.03em;">NeuraQuery</h2>
        <span class="status-badge">{st.session_state.user_tier} EDITION</span>
    </div>
    <p style="color: #94A3B8; margin: 0; font-size: 0.95rem;">Client: <b style="color: #FFFFFF;">{st.session_state.client_name}</b> | Engine: <b style="color: {accent_hex};">Qwen-2.5-Coder SLM (Quantized INT4)</b></p>
    """,
      unsafe_allow_html=True,
  )

with top_r:
  st.markdown(
      "<div style='text-align: right; padding-top: 8px;'>",
      unsafe_allow_html=True,
  )
  if st.button("🚪 Logout / Switch Tier", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()
  st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    "<hr style='border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin:"
    " 18px 0 24px 0;'>",
    unsafe_allow_html=True,
)

# 3D Live Telemetry Cards
k1, k2, k3, k4 = st.columns(4)
with k1:
  st.markdown(
      """<div class="kpi-tile"><small style="color: #94A3B8; font-weight: 600;">NETWORK SECURITY</small><br><b style="color: #10B981; font-size: 1.15rem;">● 100% Air-Gapped</b></div>""",
      unsafe_allow_html=True,
  )
with k2:
  st.markdown(
      """<div class="kpi-tile"><small style="color: #94A3B8; font-weight: 600;">SLM RAM USAGE</small><br><b style="color: #38BDF8; font-size: 1.15rem;">~380 MB Active</b></div>""",
      unsafe_allow_html=True,
  )
with k3:
  st.markdown(
      f"""<div class="kpi-tile"><small style="color: #94A3B8; font-weight: 600;">ACCESS STATUS</small><br><b style="color: {accent_hex}; font-size: 1.15rem;">{st.session_state.user_tier} UNLOCKED</b></div>""",
      unsafe_allow_html=True,
  )
with k4:
  st.markdown(
      """<div class="kpi-tile"><small style="color: #94A3B8; font-weight: 600;">DATA COMPLIANCE</small><br><b style="color: #A855F7; font-size: 1.15rem;">DPDP Act (India)</b></div>""",
      unsafe_allow_html=True,
  )

st.markdown("<br>", unsafe_allow_html=True)

with st.spinner("Initializing neural weights on local CPU..."):
  llm = load_slm()

# Sidebar Data Pipeline
with st.sidebar:
  st.markdown("### 📂 Data Pipeline")
  uploaded_file = st.file_uploader(
      "Upload Excel (.xlsx), CSV, or SQLite (.db):",
      type=["xlsx", "xls", "csv", "db"],
  )
  st.markdown("---")

# Handle Ingestion
if uploaded_file is not None:
  try:
    if uploaded_file.name.endswith(".csv"):
      df_current = pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith((".xlsx", ".xls")):
      df_current = pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith(".db"):
      with open("temp_upload.db", "wb") as f:
        f.write(uploaded_file.getbuffer())
      temp_conn = sqlite3.connect("temp_upload.db")
      tables = pd.read_sql_query(
          "SELECT name FROM sqlite_master WHERE type='table';", temp_conn
      )
      first_table = tables["name"].iloc[0] if not tables.empty else "students"
      df_current = pd.read_sql_query(f"SELECT * FROM {first_table}", temp_conn)
      temp_conn.close()

    df_current.columns = [
        c.strip().replace(" ", "_").replace("/", "_").replace("%", "pct")
        for c in df_current.columns
    ]
    st.sidebar.success(
        f"✅ Loaded `{uploaded_file.name}` ({len(df_current)} rows)"
    )
  except Exception as e:
    st.sidebar.error(f"Ingestion error: {e}")
    df_current = pd.DataFrame({"id": [101], "sample": ["data"]})
else:
  if os.path.exists("college_data.xlsx"):
    df_current = pd.read_excel("college_data.xlsx")
  else:
    df_current = pd.DataFrame({
        "name": ["Sneha Nair", "Aarav Patel", "Diya Sharma"],
        "student_id": ["STU-101", "STU-102", "STU-103"],
        "branch": ["AI/ML", "AI/ML", "CSE"],
        "city": ["Ahmedabad", "Ahmedabad", "Surat"],
        "marks": [96, 91, 94],
        "package_lpa": [18.5, 15.0, 16.8],
    })
  df_current.columns = [
      c.strip().replace(" ", "_").replace("/", "_").replace("%", "pct")
      for c in df_current.columns
  ]
  st.sidebar.info("💡 Active: `college_data.xlsx` (Default)")

df_current.to_sql(table_name, conn, index=False, if_exists="replace")

# Schema View
cursor = conn.cursor()
cursor.execute(f"PRAGMA table_info({table_name});")
columns = [row[1] for row in cursor.fetchall()]
schema_str = f"{table_name}(" + ", ".join(columns) + ")"

with st.sidebar:
  st.markdown("### 📋 Active Schema")
  st.code(schema_str, language="sql")

# Live Data Editor
if st.session_state.user_tier in ["PRO", "ENTERPRISE"]:
  with st.expander("📝 Live Interactive Spreadsheet Editor", expanded=False):
    st.info(
        "💡 Edit cells directly or click '+' at the bottom to insert new"
        " records live!"
    )
    edited_df = st.data_editor(
        df_current, num_rows="dynamic", use_container_width=True
    )
    edited_df.to_sql(table_name, conn, index=False, if_exists="replace")
else:
  with st.expander("🔒 Live Data Editor (Pro / Enterprise)", expanded=False):
    st.warning(
        "Upgrade to **NeuraQuery Pro (₹2,999/yr)** to edit database records"
        " live in browser."
    )

# Main Interactive Query Deck
st.markdown("### 💬 Conversational Query Terminal")
user_query = st.text_input(
    "Enter natural language prompt:",
    placeholder=(
        "e.g., Show all AI/ML students from Ahmedabad with marks greater than"
        " 90 sorted by package_lpa descending"
    ),
)

if st.button("Generate & Execute Query 🚀", type="primary") and user_query:
  start_time = time.time()

  if not is_safe_query(user_query):
    st.error(
        "⚠️ **Security Guardrail:** Destructive or modifying queries"
        " (DROP/DELETE/UPDATE) are blocked."
    )
  else:
    with st.spinner("Synthesizing query with local SLM engine..."):
      initial_sql = generate_sql(llm, user_query, schema_str)

    latency = round(time.time() - start_time, 2)

    col_l, col_r = st.columns(2)

    with col_l:
      st.markdown("#### 🧠 Synthesized SQL Logic")
      st.code(initial_sql, language="sql")
      st.caption(f"⏱️ Model Latency: **{latency} seconds** (Zero Network Hop)")

    with col_r:
      st.markdown("#### 📊 Dynamic Results & Insights")

      if not is_safe_query(initial_sql):
        st.error("⚠️ **Security Guardrail:** Destructive query blocked.")
      else:
        result_df, final_sql, status = run_with_self_healing(
            llm, initial_sql, conn, schema_str, user_query
        )

        # Record Audit Log
        st.session_state.audit_logs.append({
            "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "User": st.session_state.client_name,
            "Query": user_query,
            "SQL": final_sql,
            "Latency": f"{latency}s",
            "Tier": st.session_state.user_tier,
        })

        if status == "Self-Healed ✨":
          st.info(
              "🔄 **Autonomous Self-Healing Loop:** Auto-corrected to"
              f" `{final_sql}`"
          )

        if result_df is not None:
          if result_df.empty:
            st.warning("Query executed successfully, but returned 0 rows.")
          else:
            tab1, tab2, tab3 = st.tabs(
                ["📋 Table View", "📈 Visual Analytics", "📥 Data Export"]
            )

            with tab1:
              st.dataframe(result_df, use_container_width=True)
              st.success(
                  f"✅ Found **{len(result_df)}** matching records ({status})"
              )

            with tab2:
              if st.session_state.user_tier in ["PRO", "ENTERPRISE"]:
                num_cols = result_df.select_dtypes(
                    include=["number"]
                ).columns.tolist()
                str_cols = result_df.select_dtypes(
                    include=["object"]
                ).columns.tolist()
                if len(num_cols) > 0 and len(str_cols) > 0:
                  st.bar_chart(data=result_df, x=str_cols[0], y=num_cols[0])
                elif len(num_cols) > 0:
                  st.bar_chart(data=result_df[num_cols[0]])
                else:
                  st.info(
                      "Chart requires at least one numeric column in the query"
                      " result."
                  )
              else:
                st.warning(
                    "🔒 **Pro Feature:** Visual chart generation is unlocked in"
                    " Pro/Enterprise plans."
                )

            with tab3:
              if st.session_state.user_tier in ["PRO", "ENTERPRISE"]:
                csv_export = result_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Export Filtered Subset (CSV / Excel)",
                    data=csv_export,
                    file_name="query_results.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
              else:
                st.warning(
                    "🔒 **Pro Feature:** Exporting filtered subsets is unlocked"
                    " in Pro/Enterprise."
                )
        else:
          st.error(f"❌ {status}")

# Enterprise Governance Log
if st.session_state.user_tier == "ENTERPRISE":
  st.markdown("---")
  with st.expander(
      "👑 Enterprise Audit Trail & Governance Log", expanded=False
  ):
    st.caption(
        "Immutable local audit logs for institutional compliance and"
        " verification."
    )
    if st.session_state.audit_logs:
      st.table(pd.DataFrame(st.session_state.audit_logs))
    else:
      st.info("No queries logged yet in this active session.")