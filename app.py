import streamlit as st
from backend import process_loan_application

st.set_page_config(
    page_title="LoanlyFans | Loans, but make it fun",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------- Design system ----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
:root { --lime:#d5ff35; --lime2:#b9ee00; --bg:#050806; --panel:#0c110e; --muted:#a4ada4; --line:rgba(213,255,53,.22); }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:
 radial-gradient(ellipse at 12% 8%, rgba(121,157,0,.17), transparent 33%),
 radial-gradient(ellipse at 90% 65%, rgba(68,100,0,.12), transparent 32%),
 var(--bg); color:#f6f8f3; }
.block-container { max-width:1240px; padding-top:1.1rem; padding-bottom:3rem; }
header[data-testid="stHeader"] { background:transparent; }
#MainMenu, footer {visibility:hidden;}
div[data-testid="stToolbar"] {visibility:hidden;height:0;}
.brandbar { display:flex; align-items:center; justify-content:space-between; padding:20px 24px;
 border:1px solid rgba(213,255,53,.20); border-radius:18px; background:rgba(8,12,9,.88); margin-bottom:35px; }
.brand {font-family:'Space Grotesk',sans-serif;font-size:2.6rem;font-weight:700;letter-spacing:-1.5px;line-height:1.1}
.brand span {color:var(--lime)}
.brandmeta {color:#aab3a8;font-size:.76rem;letter-spacing:.03em}
.eyebrow {display:inline-block; color:var(--lime); border:1px solid rgba(213,255,53,.48); background:rgba(213,255,53,.055);
 padding:7px 13px; border-radius:99px; font-size:.7rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase;}
.hero {padding:20px 0 12px;}
.hero h1 {font-family:'Space Grotesk',sans-serif; font-size:clamp(3rem,6vw,5.6rem); line-height:.99;
 letter-spacing:-.065em; font-weight:700; margin:24px 0 20px; max-width:780px;}
.lime {color:var(--lime);}
.subhead {font-size:1.05rem;line-height:1.7;color:#c0c8be;max-width:620px}
.micro {font-size:.78rem;color:var(--muted)}
.glass {background:linear-gradient(145deg,rgba(18,25,19,.94),rgba(7,10,8,.95));border:1px solid var(--line);
 border-radius:22px;padding:24px;box-shadow:0 18px 60px rgba(0,0,0,.2);}
.step-pill {display:inline-block;padding:7px 11px;border:1px solid rgba(213,255,53,.24);border-radius:100px;color:#d7e5ce;font-size:.72rem;margin:3px 5px 3px 0}
.statbox {border:1px solid rgba(255,255,255,.09);background:rgba(255,255,255,.025);border-radius:16px;padding:15px 17px;min-height:96px}
.stat-label {font-size:.72rem;color:#aeb8ae;text-transform:uppercase;letter-spacing:.06em}
.stat-value {font-family:'Space Grotesk',sans-serif;font-size:1.35rem;font-weight:700;margin-top:7px}
.section-title {font-family:'Space Grotesk',sans-serif;font-size:1.45rem;font-weight:700;letter-spacing:-.03em}
.result-status {font-family:'Space Grotesk',sans-serif;font-size:1.2rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase}
.explanation-banner {background:linear-gradient(135deg,rgba(213,255,53,.10),rgba(213,255,53,.025));border:1px solid rgba(213,255,53,.24);border-radius:16px;padding:16px 18px;margin:12px 0 16px}
.explanation-banner strong {color:var(--lime)}
.note {color:#aab4a9;font-size:.78rem;line-height:1.55}
div[data-testid="stForm"] {border:1px solid rgba(213,255,53,.20);border-radius:20px;padding:22px;background:rgba(10,14,11,.84)}
label, .stSelectbox label, .stNumberInput label, .stTextInput label {color:#e9eee7 !important;font-size:.82rem !important;font-weight:600 !important}
input, textarea {background:#121714 !important;color:#f6f8f3 !important;border-color:#29322a !important;border-radius:10px !important}
div[data-baseweb="select"] > div {background:#121714;border-color:#29322a;border-radius:10px;color:#fff}
.stButton > button, .stFormSubmitButton > button {border-radius:999px;border:1px solid var(--lime);background:var(--lime);color:#11160a;
 font-weight:700;min-height:44px;padding:0 22px;transition:all .18s ease;}
.stButton > button:hover, .stFormSubmitButton > button:hover {background:#e4ff78;border-color:#e4ff78;color:#11160a;box-shadow:0 0 26px rgba(213,255,53,.20);transform:translateY(-1px)}
.secondary-button .stButton > button {background:transparent;color:var(--lime)}
div[data-testid="stAlert"] {border-radius:14px}
hr {border-color:rgba(255,255,255,.09)}
footer {visibility:hidden}
@media (max-width: 700px) { .brandmeta {display:none}.glass {padding:18px}.hero h1 {font-size:3rem}.brand {font-size:1.55rem}.result-status {font-size:.95rem !important;letter-spacing:.06em !important} }
</style>
""", unsafe_allow_html=True)

def header():
    st.markdown("""
<div class="brandbar">
  <div class="brand">
    <span style="font-size:2.8rem;vertical-align:middle;">💸</span>
    Loanly<span>Fans</span>
  </div>
  <div class="brandmeta">
    AI-POWERED LOAN ASSESSMENT &nbsp; · &nbsp; CLEARER DECISIONS
  </div>
</div>
""", unsafe_allow_html=True)

def stat(label, value, sub=""):
    st.markdown(f"""<div class="statbox"><div class="stat-label">{label}</div>
    <div class="stat-value">{value}</div><div class="note">{sub}</div></div>""", unsafe_allow_html=True)

def reset_app():
    for key in ["loan_result", "applicant", "exception_requested"]:
        st.session_state.pop(key, None)
    st.session_state["page"] = "welcome"

if "page" not in st.session_state:
    st.session_state.page = "welcome"
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

header()

# ------------------------------- Welcome -------------------------------
if st.session_state.page == "welcome":
    left, right = st.columns([1.15, .85], gap="large")
    with left:
        st.markdown('<div class="hero"><span class="eyebrow">✦ AI-POWERED LOAN ASSESSMENT</span>'
                    '<h1>Loans,<br>but make it <span class="lime">iconic.</span></h1>'
                    '<p class="subhead">Your money moves deserve clarity. Get a straight-up assessment, minus the finance-speak.</p></div>',
                    unsafe_allow_html=True)
        st.markdown('<span class="step-pill">◉ AI-assisted analysis</span><span class="step-pill">⬡ Policy-based checks</span><span class="step-pill">✳ Plain-English explanations</span>', unsafe_allow_html=True)
        st.write("")
        with st.form("welcome_form"):
            st.markdown("### What name are we putting on this money move? 👋")
            name = st.text_input("Your name", value=st.session_state.user_name, placeholder="Enter your name", label_visibility="collapsed")
            submitted = st.form_submit_button("Let's make moves  →", use_container_width=True)
            if submitted:
                clean_name = name.strip()
                if not clean_name:
                    st.warning("Name first. Main-character energy next.")
                else:
                    st.session_state.user_name = clean_name
                    st.session_state.page = "assessment"
                    st.rerun()
        st.markdown('<p class="note">Just your name to get started. Your financial details stay on the next screen.</p>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="glass" style="padding:10px 12px 0;overflow:hidden;">'
                    '<div style="color:#d5ff35;font-size:.72rem;letter-spacing:.14em;font-weight:700;padding:12px 12px 0">YOUR MONEY ERA STARTS HERE</div>',
                    unsafe_allow_html=True)
        st.image("assets/dog_mascot.png", use_container_width=True)
        st.markdown('<div style="font-family:Space Grotesk;font-size:1.7rem;font-weight:700;line-height:1.1;text-align:center;margin-top:-6px">Big plans. <span class="lime">Clear numbers.</span></div>'
                    '<p class="note" style="text-align:center;padding:0 12px 12px">Your next move deserves more than a confusing spreadsheet.</p></div>',
                    unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<p class="note" style="text-align:center">LoanlyFans is an educational prototype. Assessment results are preliminary and are not a lending commitment.</p>', unsafe_allow_html=True)

# ----------------------------- Assessment ------------------------------
elif st.session_state.page == "assessment":
    name = st.session_state.user_name
    st.markdown(f'<span class="eyebrow">YOUR ASSESSMENT SPACE</span><h1 style="font-family:Space Grotesk;font-size:2.8rem;letter-spacing:-.05em;margin:.7rem 0 .2rem">Welcome back, <span class="lime">{name}</span>.</h1><p class="subhead" style="font-size:.95rem">A few details, then we’ll help make the numbers make sense.</p>', unsafe_allow_html=True)
    st.markdown('<span class="step-pill">● 1. Details</span><span class="step-pill">○ 2. Assessment</span><span class="step-pill">○ 3. Results</span>', unsafe_allow_html=True)
    loan_type_choice = st.selectbox("What kind of loan are we talking?", ["🏠 Home Loan", "🧍 Personal Loan", "🚗 Vehicle Loan", "🎓 Education Loan"], key="loan_type_choice")
    loan_purpose_map = {"🏠 Home Loan":"Home", "🧍 Personal Loan":"Personal", "🚗 Vehicle Loan":"Vehicle", "🎓 Education Loan":"Education"}
    st.markdown('<div class="section-title">01 / Applicant details</div>', unsafe_allow_html=True)
    with st.form("loan_application"):
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            age = st.number_input("Age", min_value=18, max_value=100, value=30)
            gender = st.selectbox("Gender", ["Male", "Female"])
            marital_status = st.selectbox("Marital status", ["Single", "Married", "Divorced"])
            dependents = st.number_input("Dependents", min_value=0, max_value=20, value=0)
            education = st.selectbox("Education", ["Graduate", "High School", "Postgraduate"])
            employment_status = st.selectbox("Employment status", ["Employed", "Self-Employed", "Unemployed"])
            occupation_type = st.selectbox("Occupation type", ["Salaried", "Business", "Freelancer", "Professional"])
            residential_status = st.selectbox("Residential status", ["Own", "Rent", "Other"])
        with c2:
            city = st.selectbox("Area type", ["Urban", "Suburban", "Rural"])
            annual_income = st.number_input("Annual income ($)", min_value=0.0, value=80000.0, step=1000.0)
            monthly_expenses = st.number_input("Monthly expenses ($)", min_value=0.0, value=2700.0, step=100.0)
            credit_score = st.number_input("Credit score", min_value=300, max_value=900, value=700)
            existing_loans = st.number_input("Existing loans", min_value=0, max_value=30, value=0)
            total_existing_loan_amount = st.number_input("Total existing loan amount ($)", min_value=0.0, value=0.0, step=1000.0)
            outstanding_debt = st.number_input("Outstanding debt ($)", min_value=0.0, value=0.0, step=1000.0)
            loan_history = st.selectbox("Positive loan history?", ["Yes", "No"])
        with c3:
            loan_amount_requested = st.number_input("Requested loan amount ($)", min_value=5000.0, max_value=44848.0, value=20000.0, step=1000.0)
            loan_term = st.number_input("Loan term (months)", min_value=1, max_value=360, value=60)
            loan_type = st.selectbox("Loan security", ["Secured", "Unsecured"])
            co_applicant = st.selectbox("Co-applicant", ["No", "Yes"])
            bank_account_history = st.number_input("Bank account history (years)", min_value=0, max_value=50, value=5)
            transaction_frequency = st.number_input("Transaction frequency", min_value=0, max_value=1000, value=12)
            interest_rate = st.number_input("Annual interest rate (%)", min_value=0.0, max_value=100.0, value=10.0, step=.5)
        st.markdown("---")
        st.markdown('<p class="note">Please enter accurate information. This prototype does not replace lender verification or financial advice.</p>', unsafe_allow_html=True)
        submitted = st.form_submit_button("Assess my application  →", use_container_width=True)
    if submitted:
        applicant = {
            "Gender": gender, "Age": age, "Marital_Status": marital_status, "Dependents": dependents,
            "Education": education, "Employment_Status": employment_status, "Occupation_Type": occupation_type,
            "Residential_Status": residential_status, "City/Town": city, "Annual_Income": annual_income,
            "Monthly_Expenses": monthly_expenses, "Credit_Score": credit_score, "Existing_Loans": existing_loans,
            "Total_Existing_Loan_Amount": total_existing_loan_amount, "Outstanding_Debt": outstanding_debt,
            "Loan_History": 1 if loan_history == "Yes" else 0, "Loan_Amount_Requested": loan_amount_requested,
            "Loan_Term": loan_term, "Loan_Purpose": loan_purpose_map[loan_type_choice], "Interest_Rate": interest_rate,
            "Loan_Type": loan_type, "Co-Applicant": co_applicant, "Bank_Account_History": bank_account_history,
            "Transaction_Frequency": transaction_frequency,
        }
        st.session_state.applicant = applicant
        st.session_state.exception_requested = False
        st.session_state.page = "results"
        st.session_state.pop("loan_result", None)
        st.rerun()

    if st.button("← Back to welcome page", type="secondary"):
        st.session_state.page = "welcome"
        st.rerun()

# -------------------------------- Results ------------------------------
elif st.session_state.page == "results":
    if "loan_result" not in st.session_state:
        with st.spinner("Crunching the numbers so you don't have to…"):
            try:
                result = process_loan_application(
                    st.session_state.applicant,
                    exception_requested=st.session_state.get("exception_requested", False),
                    generate_message=True,
                )
                st.session_state.loan_result = result
            except Exception as e:
                st.error(f"We couldn't complete the assessment: {e}")
                if st.button("Back to application"):
                    st.session_state.page = "assessment"
                    st.rerun()
                st.stop()

    result = st.session_state.loan_result
    # Accommodate backend key variants without fabricating an outcome.
    decision = str(result.get("decision", result.get("final_decision", result.get("route", "Assessment complete")))).upper()
    probability = result.get("ml_approval_probability")
    msg = result.get("customer_message", "")
    accepted = any(x in decision for x in ["ACCEPT", "APPROV"])
    rejected = any(x in decision for x in ["REJECT", "DECLIN"])
    review = any(x in decision for x in ["REVIEW", "HUMAN", "MANUAL"])
    if accepted:
        label, icon, color = "Preliminary assessment: positive", "✓", "#d5ff35"
        headline = "Looking good."
        desc = "The preliminary assessment indicates that the application may meet the current criteria. Verification is still required."
    elif rejected:
        label, icon, color = "Preliminary assessment: not eligible", "↘", "#ff8d79"
        headline = "Let's unpack this."
        desc = "The preliminary assessment did not meet the current criteria. Review the explanation below for the supported reason and next steps."
    elif review:
        label, icon, color = "Needs a human review", "↗", "#ffd66b"
        headline = "Not a no. Not yet a yes."
        desc = "This application needs additional review. It has not been treated as a final rejection."
    else:
        label, icon, color = "Assessment completed", "✳", "#d5ff35"
        headline = "Your assessment is ready."
        desc = "Read the assessment summary below and contact the lender for confirmation."
    st.markdown('<span class="eyebrow">YOUR RESULTS ARE IN</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="glass" style="margin-top:14px"><div class="result-status" style="color:{color};font-size:1.35rem;letter-spacing:.1em">{icon} &nbsp; {label}</div><h1 style="font-family:Space Grotesk;font-size:3rem;letter-spacing:-.05em;margin:.7rem 0">{headline}</h1><p class="subhead">{desc}</p></div>', unsafe_allow_html=True)
    mascot_col, intro_col = st.columns([.32, .68], gap="medium")
    with mascot_col:
        st.image("assets/robot_mascot.png", use_container_width=True)
    with intro_col:
        st.markdown('<div class="glass" style="margin-top:18px"><div class="section-title">Your AI sidekick is on it.</div><p class="note">We checked the submitted details against the configured model and policy workflow. Read the explanation below for the supported outcome and next steps.</p><span class="step-pill">Model analysis</span><span class="step-pill">Policy checks</span><span class="step-pill">Plain-English explanation</span></div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a:
        stat("Applicant", st.session_state.user_name, "Your assessment space")
    with b:
        stat("Requested amount", f"${st.session_state.applicant['Loan_Amount_Requested']:,.0f}", st.session_state.applicant["Loan_Purpose"] + " loan")
    with c:
        stat("ML approval probability", f"{float(probability)*100:.1f}%" if probability is not None else "Not provided", "Model estimate, not a guarantee")
    st.markdown("")
    left, right = st.columns([1.35, .65], gap="large")
    with left:
        st.markdown('<div class="section-title">The explanation, minus the jargon</div>', unsafe_allow_html=True)
        st.markdown('<div class="explanation-banner"><strong>THE TAKEAWAY</strong><div style="color:#dce5d9;margin-top:5px">Here’s what your assessment means, what happens next, and what you can do from here.</div></div>', unsafe_allow_html=True)
        if msg:
            st.markdown(f'<div class="glass" style="font-size:1.02rem;line-height:1.8">{msg}</div>', unsafe_allow_html=True)
        else:
            st.info("No customer-facing explanation was returned. Check the backend/API configuration.")
    with right:
        st.markdown('<div class="section-title">What happens next?</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="glass">
          <p><span class="lime">01</span> &nbsp; Review the assessment explanation.</p>
          <hr>
          <p><span class="lime">02</span> &nbsp; Keep your supporting documents ready.</p>
          <hr>
          <p><span class="lime">03</span> &nbsp; Contact the lender for verification and a final decision.</p>
          <p class="note">LoanlyFans is a prototype. Only the lender can make the final lending decision.</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("")
    x, y = st.columns([1, 1])
    with x:
        if st.button("← Edit application", use_container_width=True, type="secondary"):
            st.session_state.page = "assessment"
            st.rerun()
    with y:
        if st.button("Start a new assessment ↗", use_container_width=True):
            reset_app()
            st.rerun()

st.markdown("<hr><p class='note' style='text-align:center'>LOANLYFANS · Your finances. Your next move. &nbsp; | &nbsp; Educational prototype only</p>", unsafe_allow_html=True)
