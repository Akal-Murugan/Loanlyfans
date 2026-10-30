"""Exported backend functions for the loan decision system."""

def calculate_financial_metrics(applicant):
    """
    applicant must contain:
      Annual_Income
      Monthly_Expenses
      Outstanding_Debt
      Total_Existing_Loan_Amount
      Loan_Amount_Requested
      Loan_Term          # months
      Interest_Rate      # annual percentage
    """

    annual_income = float(applicant["Annual_Income"])
    monthly_expenses = float(applicant["Monthly_Expenses"])
    outstanding_debt = float(applicant["Outstanding_Debt"])
    existing_loan_amount = float(
        applicant["Total_Existing_Loan_Amount"]
    )
    requested_amount = float(applicant["Loan_Amount_Requested"])
    loan_term = int(applicant["Loan_Term"])
    annual_rate = float(applicant["Interest_Rate"])

    if annual_income <= 0:
        raise ValueError("Annual income must be greater than zero.")
    if min(monthly_expenses, outstanding_debt,
           existing_loan_amount, requested_amount, annual_rate) < 0:
        raise ValueError("Financial amounts and interest rate cannot be negative.")
    if loan_term <= 0:
        raise ValueError("Loan term must be greater than zero.")

    monthly_income = annual_income / 12
    remaining_income = monthly_income - monthly_expenses

    expense_ratio = monthly_expenses / monthly_income * 100

    debt_to_income = outstanding_debt / annual_income * 100
    existing_loan_to_income = (
        existing_loan_amount / annual_income * 100
    )
    requested_loan_to_income = (
        requested_amount / annual_income * 100
    )

    # Estimate monthly repayment using a standard amortizing-loan formula.
    # This is an estimate, not a bank-issued repayment quote.
    monthly_rate = annual_rate / 100 / 12

    if monthly_rate == 0:
        monthly_repayment = requested_amount / loan_term
    else:
        monthly_repayment = (
            requested_amount * monthly_rate
            / (1 - (1 + monthly_rate) ** (-loan_term))
        )

    if remaining_income > 0:
        repayment_to_surplus = (
            monthly_repayment / remaining_income * 100
        )
    else:
        repayment_to_surplus = None

    return {
        "Annual_Income": annual_income,
        "Monthly_Income": round(monthly_income, 2),
        "Monthly_Expenses": monthly_expenses,
        "Remaining_Monthly_Income": round(remaining_income, 2),
        "Expense_to_Income_Percent": round(expense_ratio, 2),
        "Outstanding_Debt": outstanding_debt,
        "Debt_to_Annual_Income_Percent": round(debt_to_income, 2),
        "Existing_Loan_to_Annual_Income_Percent": round(
            existing_loan_to_income, 2
        ),
        "Requested_Loan_to_Annual_Income_Percent": round(
            requested_loan_to_income, 2
        ),
        "Estimated_Monthly_Repayment": round(monthly_repayment, 2),
        "Repayment_to_Surplus_Percent": (
            round(repayment_to_surplus, 2)
            if repayment_to_surplus is not None else None
        )
    }


def generate_policy_flags(applicant, metrics, exception_requested=False):
    flags = {
        "missing_or_inconsistent_data": False,
        "credit_score_review": False,
        "expense_ratio_review": False,
        "repayment_ratio_review": False,
        "zero_or_negative_surplus": False,
        "exception_requested": bool(exception_requested),
        "model_policy_conflict": False,
        "confirmed_unaffordable": False,
        "expense_ratio_over_60": False,
        "material_policy_failure": False
    }

    # Credit score rules
    credit_score = float(applicant["Credit_Score"])

    if 600 <= credit_score < 650:
        flags["credit_score_review"] = True
    elif credit_score < 600:
        # Below 600 normally declines under the policy.
        # Authorized exceptions require separate assessment.
        flags["material_policy_failure"] = True

    # Expense-to-income rules
    expense_ratio = metrics["Expense_to_Income_Percent"]

    if 40 < expense_ratio <= 60:
        flags["expense_ratio_review"] = True
    elif expense_ratio > 60:
        flags["expense_ratio_over_60"] = True

    # Remaining income rules
    surplus = metrics["Remaining_Monthly_Income"]

    if surplus <= 0:
        flags["zero_or_negative_surplus"] = True

    # Repayment-to-surplus rules
    repayment_ratio = metrics["Repayment_to_Surplus_Percent"]

    if repayment_ratio is not None:
        if 30 < repayment_ratio <= 50:
            flags["repayment_ratio_review"] = True
        elif repayment_ratio > 50:
            flags["material_policy_failure"] = True

    # Flag possible conflicts between model and policy indicators.
    # This is a review trigger, not an automatic rejection.
    if (
        any([
            flags["credit_score_review"],
            flags["expense_ratio_review"],
            flags["repayment_ratio_review"],
            flags["zero_or_negative_surplus"]
        ])
    ):
        flags["model_policy_conflict"] = True

    return flags


def route_outcome(model_prediction, policy_flags):
    """
    model_prediction: 1 / 0 or 'accepted' / 'rejected'
    policy_flags: verified results from validation and policy checks

    Example policy_flags:
      missing_or_inconsistent_data: bool
      credit_score_review: bool
      expense_ratio_review: bool
      repayment_ratio_review: bool
      zero_or_negative_surplus: bool
      confirmed_unaffordable: bool
      expense_ratio_over_60: bool
      material_policy_failure: bool
      exception_requested: bool
      model_policy_conflict: bool
    """

    prediction = str(model_prediction).strip().lower()

    if prediction in ("1", "accepted", "approve", "approved"):
        model_result = "ACCEPTED"
    elif prediction in ("0", "rejected", "reject", "declined"):
        model_result = "REJECTED"
    else:
        raise ValueError("Unrecognised model prediction.")

    review_reasons = []
    rejection_reasons = []

    # Missing or conflicting evidence must not be guessed.
    if policy_flags.get("missing_or_inconsistent_data", False):
        review_reasons.append("Missing or inconsistent information")

    if policy_flags.get("credit_score_review", False):
        review_reasons.append("Credit score requires enhanced assessment")

    if policy_flags.get("expense_ratio_review", False):
        review_reasons.append("Expense-to-income ratio requires review")

    if policy_flags.get("repayment_ratio_review", False):
        review_reasons.append("Repayment-to-surplus ratio requires review")

    if policy_flags.get("zero_or_negative_surplus", False):
        review_reasons.append("Remaining monthly income requires assessment")

    if policy_flags.get("exception_requested", False):
        review_reasons.append("Policy exception requires authorisation")

    if policy_flags.get("model_policy_conflict", False):
        review_reasons.append("Model prediction and policy assessment conflict")

    # Confirmed material failures may support rejection under policy.
    if policy_flags.get("confirmed_unaffordable", False):
        rejection_reasons.append(
            "Confirmed inability to meet proposed repayment"
        )

    if policy_flags.get("expense_ratio_over_60", False):
        rejection_reasons.append(
            "Expense-to-income ratio exceeds the normal policy limit"
        )

    if policy_flags.get("material_policy_failure", False):
        rejection_reasons.append("Material policy requirement not met")

    # Review takes precedence when facts are unresolved or an exception
    # needs consideration. Do not reject on incomplete evidence.
    if review_reasons:
        return {
            "outcome": "HUMAN_REVIEW",
            "model_prediction": model_result,
            "review_reasons": review_reasons,
            "rejection_reasons": rejection_reasons
        }

    # A policy-supported rejection takes precedence over a positive model
    # prediction. Confirm that these flags are based on verified facts.
    if rejection_reasons:
        return {
            "outcome": "REJECTED",
            "model_prediction": model_result,
            "review_reasons": [],
            "rejection_reasons": rejection_reasons
        }

    # A negative model prediction without a verified policy-grounded
    # rejection reason should be escalated, not given a fabricated reason.
    if model_result == "REJECTED":
        return {
            "outcome": "HUMAN_REVIEW",
            "model_prediction": model_result,
            "review_reasons": [
                "Model predicts rejection but no confirmed policy-grounded "
                "rejection reason has been established"
            ],
            "rejection_reasons": []
        }

    return {
        "outcome": "ACCEPTED",
        "model_prediction": model_result,
        "review_reasons": [],
        "rejection_reasons": []
    }


def get_policy_evidence(decision):
    reasons = (
        decision.get("review_reasons", [])
        + decision.get("rejection_reasons", [])
    )

    if decision["outcome"] == "ACCEPTED":
        queries = [
            "Clause 7.1 approval requirements",
            "Clause 7.3 manual review conditions"
        ]
    elif reasons:
        queries = reasons
    else:
        queries = [
            "Clause 7.2 rejection requirements",
            "Clause 7.3 manual review requirements"
        ]

    retrieved = []
    seen = set()

    for query in queries:
        for item in retrieve_policy(query, top_k=3):
            key = (item["clause_id"], item["part"])

            if key not in seen:
                seen.add(key)
                retrieved.append(item)

    return retrieved


def generate_customer_message(decision, applicant_facts=None):
    applicant_facts = applicant_facts or {}
    evidence_items = get_policy_evidence(decision)

    evidence_text = "\n\n".join(
        (
            f"Clause {item['clause_id']} — {item['title']}; "
            f"PDF pages {item['pages']}\n{item['text']}"
        )
        for item in evidence_items
    )

    outcome = decision["outcome"]

    if outcome == "ACCEPTED":
        template = """
Congratulate the applicant and explain that preliminary eligibility
criteria have been met. Ask them to submit required documents for
verification. Explicitly state that this does not guarantee final
approval or disbursement.
"""
    elif outcome == "HUMAN_REVIEW":
        template = """
Explain politely that further assessment is required. Mention only
verified review reasons supported by the supplied facts and policy.
Explain that the loan evaluation team may request further information.
Do not describe the application as rejected.
"""
    else:
        template = """
Explain the rejection respectfully and empathetically. State the
verified reason and cite the relevant policy clause. If the evidence
does not support a clear policy-based reason, do not generate a
rejection message; return the case for human review instead.
"""

    prompt = f"""
Assigned outcome: {outcome}

Verified model prediction: {decision['model_prediction']}

Verified applicant facts:
{applicant_facts}

Verified reason codes:
Review reasons: {decision['review_reasons']}
Rejection reasons: {decision['rejection_reasons']}

Retrieved policy evidence:
{evidence_text}

Required message behaviour:
{template}

Few-shot examples:
{FEW_SHOT_EXAMPLES}

Write the customer-facing message in a professional, empathetic,
formal banking tone. Use only verified facts and supporting policy
evidence. Do not invent citations or change the assigned outcome.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2
        )
    )

    return {
        "outcome": outcome,
        "message": response.text,
        "sources": evidence_items
    }


def process_loan_application(
    applicant_data,
    exception_requested=False
):
    """
    Coordinates the ML model, financial calculations,
    policy routing, RAG retrieval and Gemini explanation.
    """

    # 1. Validate required ML features
    missing_features = [
        col for col in ML_FEATURES
        if col not in applicant_data
    ]

    if missing_features:
        raise ValueError(
            f"Missing required ML features: {missing_features}"
        )

    # 2. Prepare model input in the exact expected order
    model_input = pd.DataFrame(
        [{col: applicant_data[col] for col in ML_FEATURES}],
        columns=ML_FEATURES
    )

    # 3. Run the ML pipeline
    approval_probability = float(
        ml_pipeline.predict_proba(model_input)[0, 1]
    )

    model_prediction = int(
        approval_probability >= ML_THRESHOLD
    )

    # 4. Calculate financial metrics
    metrics = calculate_financial_metrics(applicant_data)

    # 5. Generate policy flags
    policy_flags = generate_policy_flags(
        applicant_data,
        metrics,
        exception_requested=exception_requested
    )

    # 6. Route the outcome
    decision = route_outcome(
        model_prediction=model_prediction,
        policy_flags=policy_flags
    )

    # 7. Assemble verified facts for the explanation
    applicant_facts = {
        **applicant_data,
        **metrics,
        "ml_prediction": model_prediction,
        "ml_approval_probability": round(
            approval_probability, 4
        ),
        "policy_flags": policy_flags,
        "routed_outcome": decision["outcome"]
    }

    # 8. Generate customer-facing explanation using existing RAG + Gemini
    message_result = generate_customer_message(
        decision,
        applicant_facts=applicant_facts
    )

    return {
        "applicant_facts": applicant_facts,
        "ml_prediction": model_prediction,
        "ml_approval_probability": approval_probability,
        "financial_metrics": metrics,
        "policy_flags": policy_flags,
        "decision": decision,
        "customer_message": message_result["message"],
        "policy_sources": message_result.get("sources", [])
    }


