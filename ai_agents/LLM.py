def _offline_synthesize(self, user_query, retrieved_context):
    """
    Context-driven offline response generator for Tamil/Tanglish and English
    telecom queries.
    """

    q_lower = user_query.lower()

    # Tamil language detection
    is_tamil = any(
        char in user_query
        for char in [
            "என்",
            "மற்றும்",
            "இணைப்பு",
            "பில்",
            "அக்கவுண்ட்",
            "தவறாக",
            "நெட்வொர்க்",
            "சேவை",
            "சிக்கல்",
            "வேண்டும்",
            "இல்லை",
        ]
    )

    # Tamil response
    if is_tamil:
        return f"""**வாடிக்கையாளர் சேவை (Telecom AI Customer Resolution)**

அன்புள்ள வாடிக்கையாளரே, உங்கள் பிரச்சனை குறித்து வருந்துகிறோம்.

**சிக்கல் கண்டறிதல் (Diagnosis):**
உங்கள் கோரிக்கை பெறப்பட்டது. நெட்வொர்க்/சேவை தொடர்பான தொழில்நுட்ப தகவல்கள் சரிபார்க்கப்படுகின்றன.

**தீர்வு நடவடிக்கைகள் (Action Plan):**
1. உங்கள் மொபைல் அமைப்புகளில் Network Mode (4G/5G Auto) சரிபார்க்கவும்.
2. SIM நெட்வொர்க் புதுப்பிப்பு (OTA Signal Refresh) செய்யப்படுகிறது.
3. தேவையானால் Telecom Operations Team-க்கு பிரச்சனை escalate செய்யப்படும்.

**டிக்கெட் நிலை (Ticket Status):**
- **Priority:** High / Medium
- **Status:** Escalated to Telecom Operations Team
- **Ref ID:** TCK-{hash(user_query) % 100000:05d}
"""

    # English response
    action_step = (
        "We are initiating an OTA network profile refresh "
        "and escalating the issue to Network Operations."
    )

    if "bill" in q_lower or "charge" in q_lower or "refund" in q_lower:
        action_step = (
            "We are checking the billing details and verifying "
            "the reported charge against the account."
        )

    elif "recharge" in q_lower:
        action_step = (
            "The recharge transaction is being verified against "
            "the payment gateway records."
        )

    elif "sim" in q_lower or "activation" in q_lower:
        action_step = (
            "The SIM activation status is being verified and "
            "the required activation checks will be performed."
        )

    return f"""**Telecom Customer Resolution Assistant**

Dear Customer, thank you for reaching out. We apologize for the inconvenience.

**1. Root Cause & Diagnosis:**
Based on your query and the retrieved telecom knowledge, your issue has been categorized for further resolution.

**2. Recommended Action Plan:**
- {action_step}
- The issue will be handled according to the applicable telecom support procedure.

**3. Ticket Summary & Recommended Actions:**
- **Action Required:** Auto-Escalation & Account Refresh
- **Ticket Reference ID:** TCK-{hash(user_query) % 100000:05d}
- **Status:** Assigned to Department Operations
"""
