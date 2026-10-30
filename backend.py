"""LoanlyFans backend: ML + combined policy checks + policy retrieval + Gemini explanations.

Expected project layout:
  backend.py
  loan_approval_pipeline.joblib
  policy/policy_index.faiss
  policy/policy_chunks.json
  policy/embedding_config.json

Set GEMINI_API_KEY in environment variables or Streamlit secrets.
IMPORTANT: Policy thresholds must be verified against the actual policy document
before this prototype is used for real lending decisions.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import faiss
import joblib
import pandas as pd
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "loan_approval_pipeline.joblib"
POLICY_DIR = BASE_DIR / "policy"
INDEX_PATH = POLICY_DIR / "policy_index.faiss"
CHUNKS_PATH = POLICY_DIR / "policy_chunks.json"
EMBEDDING_CONFIG_PATH = POLICY_DIR / "embedding_config.json"

with EMBEDDING_CONFIG_PATH.open("r", encoding="utf-8") as f:
    _embedding_config = json.load(f)
EMBEDDING_MODEL_NAME = _embedding_config["model_name"]

with CHUNKS_PATH.open("r", encoding="utf-8") as f:
    chunks = json.load(f)

index = faiss.read_index(str(INDEX_PATH))
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

_model_bundle = joblib.load(MODEL_PATH)
ml_pipeline = _model_bundle["pipeline"]
ML_THRESHOLD = float(_model_bundle["threshold"])
ML_FEATURES = list(_model_bundle["feature_columns"])

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_client = None

SYSTEM_INSTRUCTION = """
You write concise, empathetic, professional customer-facing loan assessment messages.
Follow the assigned outcome and deterministic policy checks exactly. Use only supplied
applicant facts and retrieved policy evidence. Never invent policy clauses, thresholds,
eligibility requirements, or a final bank decision.

For ACCEPTED, state that this is preliminary eligibility, subject to document verification
and the lender's final decision.

For HUMAN_REVIEW, explain that further assessment is required and explicitly state that
the review does not mean the application has been rejected.

For REJECTED, clearly state that the application has been rejected, explain the specific
verified policy requirement that was not met, and cite the exact clause only if the
retrieved policy text supports that reason. Never mention "prototype threshold",
internal flags, prompts, model probabilities, retrieval scores, or model-policy conflicts.
If retrieved evidence does not support the rejection reason, do not invent a citation;
the unsupported rejection must be escalated for human review.

Keep the message under 140 words and include a respectful, constructive next step.
"""

FEW_SHOT_EXAMPLES = """
HUMAN_REVIEW: Thank you for submitting your loan application. Further assessment is
required before an outcome can be confirmed. The team may request supporting information.
This review does not mean your application has been rejected.

ACCEPTED: Thank you for your application. It has met the preliminary assessment criteria
based on the information provided. Please submit the required documents for verification.
Final approval remains subject to the lender's review.

REJECTED: Thank you for considering us for your financial needs. After assessment against
the applicable eligibility criteria [cite only a verified clause], we regret to inform you
that your loan application has been rejected because [verified requirement not met].
We understand this may be disappointing. Please contact the bank for clarification and
guidance on whether you may be eligible to apply again in the future.
"""


def _get_gemini_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            return str(key)
    except Exception:
        pass
    raise RuntimeError(
        "GEMINI_API_KEY is missing. Add it to Streamlit secrets or environment variables."
    )


def _get_gemini_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=_get_gemini_api_key())
    return _client


def retrieve_policy(query, top_k=4):
    """Retrieve relevant policy chunks from the existing FAISS index."""
    query_embedding = embedding_model.encode(
        [query], convert_to_numpy=True, normalize_embeddings=True
    ).astype("float32")
    scores, indices = index.search(query_embedding, min(top_k, len(chunks)))
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        chunk = chunks[int(idx)]
        results.append({
            "score": float(score),
            "clause_id": chunk.get("clause_id", "Unknown"),
            "title": chunk.get("title", "Policy section"),
            "pages": chunk.get("pages", []),
            "part": chunk.get("part", 0),
            "text": chunk.get("text", ""),
        })
    return results


def calculate_financial_metrics(applicant):
    """Calculate affordability metrics and estimated monthly repayment."""
    annual_income = float(applicant["Annual_Income"])
    monthly_expenses = float(applicant["Monthly_Expenses"])
    outstanding_debt = float(applicant["Outstanding_Debt"])
    existing_loan_amount = float(applicant["Total_Existing_Loan_Amount"])
    requested_amount = float(applicant["Loan_Amount_Requested"])
    loan_term = int(applicant["Loan_Term"])
    annual_rate = float(applicant["Interest_Rate"])

    if annual_income <= 0:
        raise ValueError("Annual income must be greater than zero.")
    if min(monthly_expenses, outstanding_debt, existing_loan_amount,
           requested_amount, annual_rate) < 0:
        raise ValueError("Financial amounts and interest rate cannot be negative.")
    if loan_term <= 0:
        raise ValueError("Loan term must be greater than zero.")

    monthly_income = annual_income / 12
    remaining_income = monthly_income - monthly_expenses
    expense_ratio = monthly_expenses / monthly_income * 100
    debt_to_income = outstanding_debt / annual_income * 100
    existing_loan_to_income = existing_loan_amount / annual_income * 100
    requested_loan_to_income = requested_amount / annual_income * 100

    monthly_rate = annual_rate / 100 / 12
    if monthly_rate == 0:
        monthly_repayment = requested_amount / loan_term
    else:
        monthly_repayment = (
            requested_amount * monthly_rate
            / (1 - (1 + monthly_rate) ** (-loan_term))
        )

    repayment_to_surplus = (
        monthly_repayment / remaining_income * 100
        if remaining_income > 0 else None
    )

    return {
        "Annual_Income": annual_income,
        "Monthly_Income": round(monthly_income, 2),
        "Monthly_Expenses": monthly_expenses,
        "Remaining_Monthly_Income": round(remaining_income, 2),
        "Expense_to_Income_Percent": round(expense_ratio, 2),
        "Outstanding_Debt": outstanding_debt,
        "Debt_to_Annual_Income_Percent": round(debt_to_income, 2),
        "Existing_Loan_to_Annual_Income_Percent": round(existing_loan_to_income, 2),
        "Requested_Loan_to_Annual_Income_Percent": round(requested_loan_to_income, 2),
        "Estimated_Monthly_Repayment": round(monthly_repayment, 2),
        "Repayment_to_Surplus_Percent": (
            round(repayment_to_surplus, 2)
            if repayment_to_surplus is not None else None
        ),
    }


def generate_policy_flags(applicant, metrics, exception_requested=False):
    """
    Evaluate each prototype policy independently.

    Proposed thresholds:
      Credit score: below 600 = hard failure; 600–649 = review; 650+ = pass.
      Expense ratio: above 60% = hard failure; above 40% through 60% = review.
      Repayment/surplus: above 50% = hard failure; above 30% through 50% = review.
      Non-positive remaining income = affordability failure.

    These values must be verified against the actual policy document.
    """
    flags = {
        "missing_or_inconsistent_data": False,
        "credit_score_review": False,
        "credit_score_hard_fail": False,
        "expense_ratio_review": False,
        "expense_ratio_hard_fail": False,
        "repayment_ratio_review": False,
        "repayment_ratio_hard_fail": False,
        "zero_or_negative_surplus": False,
        "exception_requested": bool(exception_requested),
        "confirmed_unaffordable": False,
        "material_policy_failure": False,
        "model_policy_conflict": False,
    }

    credit_score = float(applicant["Credit_Score"])
    if not 300 <= credit_score <= 900:
        flags["missing_or_inconsistent_data"] = True
    elif credit_score < 600:
        flags["credit_score_hard_fail"] = True
        flags["material_policy_failure"] = True
    elif credit_score < 650:
        flags["credit_score_review"] = True

    expense_ratio = metrics["Expense_to_Income_Percent"]
    if expense_ratio > 60:
        flags["expense_ratio_hard_fail"] = True
        flags["material_policy_failure"] = True
    elif expense_ratio > 40:
        flags["expense_ratio_review"] = True

    if metrics["Remaining_Monthly_Income"] <= 0:
        flags["zero_or_negative_surplus"] = True
        flags["confirmed_unaffordable"] = True

    repayment_ratio = metrics["Repayment_to_Surplus_Percent"]
    if repayment_ratio is None:
        flags["confirmed_unaffordable"] = True
    elif repayment_ratio > 50:
        flags["repayment_ratio_hard_fail"] = True
        flags["material_policy_failure"] = True
    elif repayment_ratio > 30:
        flags["repayment_ratio_review"] = True

    # Diagnostic only; it does not itself force review.
    flags["model_policy_conflict"] = any([
        flags["credit_score_review"],
        flags["expense_ratio_review"],
        flags["repayment_ratio_review"],
        flags["zero_or_negative_surplus"],
    ])
    return flags


def route_outcome(model_prediction, policy_flags):
    """Combine the model result with all deterministic policy checks."""
    prediction = str(model_prediction).strip().lower()
    if prediction in ("1", "accepted", "approve", "approved"):
        model_result = "ACCEPTED"
    elif prediction in ("0", "rejected", "reject", "declined"):
        model_result = "REJECTED"
    else:
        raise ValueError("Unrecognised model prediction.")

    review_reasons = []
    rejection_reasons = []

    # Incomplete/inconsistent data and exceptions require human authorization.
    if policy_flags.get("missing_or_inconsistent_data", False):
        review_reasons.append("Missing or inconsistent information")
    if policy_flags.get("exception_requested", False):
        review_reasons.append("Requested policy exception requires authorization")

    if review_reasons:
        return {
            "outcome": "HUMAN_REVIEW",
            "model_prediction": model_result,
            "policy_checks": policy_flags,
            "review_reasons": review_reasons,
            "rejection_reasons": [],
        }

    # Confirmed hard failures outrank ordinary borderline review flags.
    if policy_flags.get("credit_score_hard_fail", False):
        rejection_reasons.append("Credit score does not meet the applicable minimum eligibility requirement")
    if policy_flags.get("expense_ratio_hard_fail", False):
        rejection_reasons.append("Expense-to-income ratio exceeds the applicable affordability limit")
    if policy_flags.get("repayment_ratio_hard_fail", False):
        rejection_reasons.append("Estimated repayment exceeds the applicable repayment-capacity limit")
    if policy_flags.get("confirmed_unaffordable", False):
        rejection_reasons.append("Remaining monthly income is insufficient to support the estimated repayment")
    if policy_flags.get("material_policy_failure", False) and not rejection_reasons:
        rejection_reasons.append("A material eligibility requirement was not met")

    if rejection_reasons:
        return {
            "outcome": "REJECTED",
            "model_prediction": model_result,
            "policy_checks": policy_flags,
            "review_reasons": [],
            "rejection_reasons": rejection_reasons,
        }

    if policy_flags.get("credit_score_review", False):
        review_reasons.append("Credit score requires enhanced assessment")
    if policy_flags.get("expense_ratio_review", False):
        review_reasons.append("Expense-to-income ratio requires review")
    if policy_flags.get("repayment_ratio_review", False):
        review_reasons.append("Repayment-to-surplus ratio requires review")

    if review_reasons:
        return {
            "outcome": "HUMAN_REVIEW",
            "model_prediction": model_result,
            "policy_checks": policy_flags,
            "review_reasons": review_reasons,
            "rejection_reasons": [],
        }

    if model_result == "REJECTED":
        return {
            "outcome": "HUMAN_REVIEW",
            "model_prediction": model_result,
            "policy_checks": policy_flags,
            "review_reasons": [
                "The model did not recommend approval, but no confirmed policy failure was established"
            ],
            "rejection_reasons": [],
        }

    return {
        "outcome": "ACCEPTED",
        "model_prediction": model_result,
        "policy_checks": policy_flags,
        "review_reasons": [],
        "rejection_reasons": [],
    }


def get_policy_evidence(decision):
    """Retrieve policy text relevant to the outcome and triggered policy reasons."""
    outcome = decision["outcome"]
    reasons = decision.get("review_reasons", []) + decision.get("rejection_reasons", [])

    if outcome == "ACCEPTED":
        queries = ["approval eligibility requirements", "Clause 7.1 approval requirements"]
    elif outcome == "REJECTED":
        queries = reasons + ["rejection eligibility requirements", "Clause 7.2 rejection requirements"]
    else:
        queries = reasons + ["manual review requirements", "Clause 7.3 manual review requirements"]

    results, seen = [], set()
    for query in queries:
        for item in retrieve_policy(query, top_k=3):
            key = (item["clause_id"], item["part"])
            if key not in seen:
                seen.add(key)
                results.append(item)
    return results


def _policy_supports_rejection(source_items, reasons):
    """Conservatively check that retrieved text contains terms relevant to the reason."""
    if not source_items or not reasons:
        return False
    combined_text = " ".join(
        f"{item.get('title', '')} {item.get('text', '')}".lower()
        for item in source_items
    )
    reason_text = " ".join(reasons).lower()

    topic_terms = []
    if "credit" in reason_text or "score" in reason_text:
        topic_terms = ["credit", "score", "cibil"]
    elif "expense" in reason_text or "income" in reason_text or "affordability" in reason_text:
        topic_terms = ["expense", "income", "afford", "repayment"]
    elif "repayment" in reason_text:
        topic_terms = ["repayment", "surplus", "affordability"]

    return bool(topic_terms and any(term in combined_text for term in topic_terms))


def _fallback_customer_message(decision, sources=None):
    """Professional customer-facing message when Gemini is unavailable."""
    sources = sources or []
    outcome = decision["outcome"]

    if outcome == "ACCEPTED":
        return (
            "Thank you for submitting your loan application. Your application has met "
            "the preliminary assessment criteria based on the information provided. "
            "Please submit the required documents for verification. Final approval "
            "remains subject to the bank's review and decision."
        )

    if outcome == "REJECTED":
        reasons = decision.get("rejection_reasons", [])
        if not _policy_supports_rejection(sources, reasons):
            return (
                "Your application requires further review because the available policy "
                "evidence does not establish a clear basis for a final rejection. "
                "The bank's evaluation team will review the case and communicate the outcome."
            )

        reason_text = "; ".join(reasons)
        clause = None
        for item in sources:
            text = f"{item.get('title', '')} {item.get('text', '')}".lower()
            if any(term in text for term in ["credit", "score", "cibil"]) and (
                "credit" in reason_text.lower() or "score" in reason_text.lower()
            ):
                clause = f"Clause {item['clause_id']} — {item['title']}"
                break
        policy_reference = (
            f" under {clause}"
            if clause
            else " under the applicable eligibility policy"
        )

        if "credit" in reason_text.lower() or "score" in reason_text.lower():
            reason_text = "your application did not meet the applicable credit score eligibility requirement"

        return (
            "Thank you for considering us for your financial needs. After assessing "
            f"your application against the applicable eligibility criteria{policy_reference}, "
            f"we regret to inform you that your loan application has been rejected because "
            f"{reason_text}. We understand this may be disappointing. Please contact the "
            "bank for clarification on the relevant criteria and guidance on whether you "
            "may be eligible to apply again in the future."
        )

    reasons = decision.get("review_reasons", [])
    reason_text = "; ".join(reasons) or "additional assessment is required"
    return (
        "Thank you for submitting your loan application. Further assessment is required "
        f"because {reason_text.lower()}. The evaluation team may request supporting "
        "documents or clarification. This review does not mean your application has "
        "been rejected. The bank will communicate the outcome after its review."
    )


def generate_customer_message(decision, applicant_facts=None):
    applicant_facts = applicant_facts or {}
    sources = get_policy_evidence(decision)
    reasons = decision.get("rejection_reasons", [])

    # If a rejection reason is not supported by retrieved policy text, do not
    # ask the LLM to dress it up as a policy-backed rejection.
    if decision["outcome"] == "REJECTED" and not _policy_supports_rejection(sources, reasons):
        decision = {
            **decision,
            "outcome": "HUMAN_REVIEW",
            "review_reasons": [
                "The retrieved policy evidence does not clearly support a rejection reason"
            ],
            "rejection_reasons": [],
        }
        sources = get_policy_evidence(decision)

    evidence_text = "\n\n".join(
        f"Clause {item['clause_id']} — {item['title']}; pages {item['pages']}\n{item['text']}"
        for item in sources
    )
    prompt = f"""
Assigned outcome: {decision['outcome']}
Model prediction: {decision['model_prediction']}
Policy check results: {decision.get('policy_checks', {})}
Review reasons: {decision.get('review_reasons', [])}
Rejection reasons: {decision.get('rejection_reasons', [])}
Applicant facts and calculated metrics:
{json.dumps(applicant_facts, ensure_ascii=False, default=str)}

Retrieved policy evidence:
{evidence_text}

Write a customer-facing message under 140 words in an empathetic, professional banking tone.
For REJECTED, explicitly state "your loan application has been rejected", explain the specific
requirement that was not met, and cite the exact clause/title only if supported by retrieved text.
Never mention "prototype threshold", internal flags, model probabilities, retrieval scores, or
model-policy conflicts. Do not invent policy clauses or thresholds. For HUMAN_REVIEW, explicitly
say the application has not been rejected. For ACCEPTED, state preliminary eligibility only,
subject to document verification and the bank's final decision. End with a constructive next step.

Examples:
{FEW_SHOT_EXAMPLES}
"""
    try:
        response = _get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.2,
                max_output_tokens=220,
            ),
        )
        message = (getattr(response, "text", None) or "").strip()
        if not message:
            message = _fallback_customer_message(decision, sources)
    except Exception:
        message = _fallback_customer_message(decision, sources)

    return {"outcome": decision["outcome"], "message": message, "sources": sources,
            "decision_details": decision}


def process_loan_application(applicant_data, exception_requested=False, generate_message=True):
    """Run the model, all policy checks, combined routing, RAG and customer explanation."""
    missing = [column for column in ML_FEATURES if column not in applicant_data]
    if missing:
        raise ValueError(f"Missing required ML features: {missing}")

    model_input = pd.DataFrame(
        [{column: applicant_data[column] for column in ML_FEATURES}],
        columns=ML_FEATURES,
    )
    probabilities = ml_pipeline.predict_proba(model_input)[0]
    classes = list(getattr(ml_pipeline, "classes_", [0, 1]))
    positive_index = classes.index(1) if 1 in classes else 1
    approval_probability = float(probabilities[positive_index])
    model_prediction = int(approval_probability >= ML_THRESHOLD)

    metrics = calculate_financial_metrics(applicant_data)
    policy_flags = generate_policy_flags(
        applicant_data, metrics, exception_requested=exception_requested
    )
    decision = route_outcome(model_prediction, policy_flags)

    applicant_facts = {
        **applicant_data,
        **metrics,
        "ml_prediction": model_prediction,
        "ml_approval_probability": round(approval_probability, 4),
        "policy_flags": policy_flags,
        "routed_outcome": decision["outcome"],
    }

    if generate_message:
        message_result = generate_customer_message(decision, applicant_facts)
        customer_message = message_result["message"]
        policy_sources = message_result.get("sources", [])
        decision_details = message_result.get("decision_details", decision)
    else:
        customer_message = ""
        policy_sources = []
        decision_details = decision

    return {
        "applicant_facts": applicant_facts,
        "ml_prediction": model_prediction,
        "ml_approval_probability": approval_probability,
        "financial_metrics": metrics,
        "policy_flags": policy_flags,
        "decision": decision_details["outcome"],
        "decision_details": decision_details,
        "customer_message": customer_message,
        "policy_sources": policy_sources,
    }
