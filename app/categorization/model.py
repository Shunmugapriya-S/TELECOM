"""
app/categorization/model.py

Category + sub-category classification (TF-IDF + SVM).
Import predict_category(text) from main.py.

Requires, in this same folder:
    tfidf_vectorizer.pkl
    svm_category_model.pkl
    svm_subcategory_model.pkl
"""

import re
import os
import joblib

_DIR = os.path.dirname(os.path.abspath(__file__))

_tfidf = joblib.load(os.path.join(_DIR, "tfidf_vectorizer.pkl"))
_svm_category = joblib.load(os.path.join(_DIR, "svm_category_model.pkl"))
_svm_subcategory = joblib.load(os.path.join(_DIR, "svm_subcategory_model.pkl"))

# The SVM predicts category and sub_category as two SEPARATE classifiers,
# which can disagree with each other (e.g. category="Network" paired with
# sub_category="In-Building Coverage Issue", which actually belongs to
# "Coverage & Infrastructure"). This breaks the priority dictionary lookup,
# since that dictionary only contains valid category+sub_category pairs.
#
# Fix: sub_category is the more specific, more reliable signal, so we
# always DERIVE category from sub_category using this fixed mapping,
# rather than trusting the SVM's separate category prediction. This
# guarantees every (category, sub_category) pair this function returns
# is a valid, priority-dictionary-matchable combination.
SUBCATEGORY_TO_CATEGORY = {
    "4G Problem": "Network",
    "5G Problem": "Network",
    "Account Suspension/Reactivation": "Account",
    "Activation Issue": "Service Request",
    "Add-on/Pack Subscription Issue": "Value-Added Services (VAS)",
    "Auto-Debit/Auto-Pay Failure": "Billing",
    "Auto-Recharge Cancellation": "Recharge",
    "Balance Check": "Account",
    "Bandwidth Throttling Complaint": "Network",
    "Battery/Charging Problem": "Device",
    "Broadband Problem": "Network",
    "Call Drop": "Network",
    "Callback Request": "Customer Experience",
    "Caller Tune/Ringtone Issue": "Value-Added Services (VAS)",
    "Cancellation": "Service Request",
    "Compensation/Goodwill Request": "Customer Experience",
    "Complaint Escalation": "Customer Experience",
    "Data Privacy Complaint": "Fraud & Security",
    "Device Compatibility Issue": "Device",
    "Duplicate Charge": "Billing",
    "Duplicate SIM Issue": "SIM",
    "Failed Recharge": "Recharge",
    "Family/Group Plan Management": "Plan",
    "Feedback": "Customer Experience",
    "Firmware/OS Update Failure": "Device",
    "Hardware Defect/Warranty Claim": "Device",
    "IVR Navigation Difficulty": "Customer Experience",
    "In-Building Coverage Issue": "Coverage & Infrastructure",
    "Installation/Technician Visit Scheduling": "Service Request",
    "Insurance/Add-on Service Cancellation": "Value-Added Services (VAS)",
    "International Roaming Issue": "Plan",
    "Invoice Not Received": "Billing",
    "KYC/Document Verification": "Account",
    "Late Payment Penalty Dispute": "Billing",
    "Login/Password Reset": "Account",
    "Long Wait Time/Hold Time": "Customer Experience",
    "New Connection Request": "Service Request",
    "New Tower Request": "Coverage & Infrastructure",
    "No Signal": "Network",
    "OTT Subscription Bundling Problem": "Value-Added Services (VAS)",
    "Outage Check": "Network",
    "Ownership Transfer Request": "Account",
    "Phishing/Scam Call Report": "Fraud & Security",
    "Plan Change": "Plan",
    "Plan Downgrade Request": "Plan",
    "Plan Expiry/Renewal Confusion": "Plan",
    "Plan Recommendation": "Plan",
    "Porting (MNP) Delay/Failure": "Service Request",
    "Profile Update": "Account",
    "Promotional Discount Not Applied": "Billing",
    "Recharge Not Reflecting": "Recharge",
    "Router/Modem Configuration Issue": "Device",
    "Rude Agent Behavior": "Customer Experience",
    "Rural/Remote Area Connectivity": "Coverage & Infrastructure",
    "SIM Damaged/Lost": "SIM",
    "SIM Swap Request": "SIM",
    "Service Upgrade Request": "Service Request",
    "Slow Internet": "Network",
    "Software Issue": "Device",
    "Store/Outlet Service Complaint": "Customer Experience",
    "Tax/GST Calculation Error": "Billing",
    "Third-Party Recharge Platform Issue": "Recharge",
    "Ticket Status": "Customer Experience",
    "Two-Factor Authentication Issue": "Fraud & Security",
    "Unauthorized Charge/Fraudulent Transaction": "Fraud & Security",
    "Unauthorized SIM Swap": "Fraud & Security",
    "Unexpected Bill": "Billing",
    "Unwanted VAS Auto-Subscription": "Value-Added Services (VAS)",
    "Usage Dispute": "Billing",
    "VoLTE/HD Voice Problem": "Network",
    "Wrong Charge": "Billing",
    "Wrong Recharge Applied": "Recharge",
    "eSIM Provisioning Issue": "SIM",
}


def _clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def predict_category(raw_text: str) -> dict:
    """
    Input: complaint text (English).
    Output: predicted category and sub_category - guaranteed to be a
    VALID pair (category is derived from sub_category, not taken from
    the SVM's separate, sometimes-inconsistent category prediction).
    """
    cleaned = _clean_text(raw_text)
    vec = _tfidf.transform([cleaned])

    predicted_subcategory = _svm_subcategory.predict(vec)[0]
    # derive category from sub_category - guaranteed valid pair
    derived_category = SUBCATEGORY_TO_CATEGORY.get(predicted_subcategory)

    if derived_category is None:
        # sub_category not in our known mapping (shouldn't normally happen) -
        # fall back to the SVM's own category prediction as a last resort
        derived_category = _svm_category.predict(vec)[0]

    return {
        "category": derived_category,
        "sub_category": predicted_subcategory,
    }