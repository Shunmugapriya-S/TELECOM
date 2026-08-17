import os
import sys
import time
import uuid
import importlib.util
from typing import List, Dict, Any, Optional
from pathlib import Path

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent   # …/rag_engine/backend
RAG_ENGINE_DIR = BACKEND_DIR.parent             # …/rag_engine
BACKEND_APP_DIR = BACKEND_DIR / "app"          # …/rag_engine/backend/app

# NOTE: rag_engine/app.py shadows backend/app/ package if rag_engine is on path.
# We use importlib to load backend/app/* modules directly by file path so
# there is zero ambiguity regardless of CWD or sys.path ordering.

def _load_module(module_name: str, file_path: Path):
    """Load a python module directly from its absolute file path."""
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod

# Load backend/app submodules by absolute path to avoid the app.py collision
_recorder_mod    = _load_module("backend_app.recorder",       BACKEND_APP_DIR / "recorder.py")
_stt_mod         = _load_module("backend_app.stt_engine",     BACKEND_APP_DIR / "stt_engine.py")
_noise_mod       = _load_module("backend_app.noise_reduction", BACKEND_APP_DIR / "noise_reduction.py")
_tts_mod         = _load_module("backend_app.tts_engine",     BACKEND_APP_DIR / "tts_engine.py")
_db_mod          = _load_module("backend_app.db",             BACKEND_APP_DIR / "db.py")

# text_correction requires GROQ_API_KEY – load gracefully
try:
    _correction_mod  = _load_module("backend_app.text_correction", BACKEND_APP_DIR / "text_correction.py")
except Exception as _tc_err:
    print(f"[Warning] text_correction module unavailable (GROQ_API_KEY not set?): {_tc_err}")
    _correction_mod = None

record_audio           = _recorder_mod.record_audio
transcribe_speech      = _stt_mod.transcribe_speech
transcribe_to_english  = _stt_mod.transcribe_to_english
clean_audio            = _noise_mod.clean_audio
understand_transcript  = getattr(_correction_mod, "understand_transcript", None) if _correction_mod else None
speak_text             = _tts_mod.speak_text
db                     = _db_mod

# Add rag_engine root for langgraph_orchestrator (safe here — it's a .py not a package)
if str(RAG_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_ENGINE_DIR))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import urllib.request
import json

# LangGraph Orchestrator import
from langgraph_orchestrator import TelecomLangGraphOrchestrator

app = FastAPI(
    title="Telecom RAG & Voice Pipeline Backend",
    description="Unified API server connecting WhatsApp Gateway, Speech-To-Text, LangGraph Orchestration, Human Escalation, and Executive UI Dashboard.",
    version="2.0.0"
)

# CORS middleware for local frontend Vite server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create audio directories & static file mount
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio_input")
os.makedirs(AUDIO_DIR, exist_ok=True)
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# Mount frontend web dashboard for Unified Port execution
FRONTEND_DIST_DIR = RAG_ENGINE_DIR / "sahaya-voice-project" / "frontend" / "dist"
if (FRONTEND_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets")), name="frontend_assets")

# Initialize LangGraph Orchestrator singleton
orchestrator = TelecomLangGraphOrchestrator()


# In-memory ticket database for live executive dashboard tracking
tickets_db: List[Dict[str, Any]] = [
    {
        "id": "TICK-1001",
        "user_id": "+919876543210",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "input_type": "voice",
        "raw_transcript": "Ennoda 5G network varala, and billing sum $60 extra vandhuruku",
        "english_translation": "My 5G network is not working, and an extra $60 charge appeared on my bill",
        "category": "Billing",
        "sub_category": "Wrong Charge",
        "sentiment": "Negative",
        "emotion": "Anger",
        "priority": "High",
        "priority_score": 8.8,
        "status": "escalated_to_human",
        "escalated_to_human": True,
        "ai_response": "We understand your frustration regarding the $60 billing charge and 5G network issue. Your ticket has been prioritized.",
        "human_resolution": None,
        "resolved_at": None
    },
    {
        "id": "TICK-1002",
        "user_id": "+919812345678",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "input_type": "text",
        "raw_transcript": "How do I activate international roaming on prepaid?",
        "english_translation": "How do I activate international roaming on prepaid?",
        "category": "Plan",
        "sub_category": "Plan Change",
        "sentiment": "Neutral",
        "emotion": "Calm",
        "priority": "Medium",
        "priority_score": 5.2,
        "status": "resolved_by_ai",
        "escalated_to_human": False,
        "ai_response": "To activate international roaming on prepaid, open the Telecom App -> Services -> International Roaming -> Select Pack.",
        "human_resolution": None,
        "resolved_at": None
    }
]

# Standard retry messages
STT_RETRY_MESSAGES = {
    "no_speech_detected": "I didn't catch any speech in that recording. Please try again.",
    "likely_silence_or_noise": "That sounded like silence or background noise. Please try again in a quieter spot.",
    "low_confidence_transcription": "I couldn't hear that clearly enough. Could you repeat that closer to the mic?",
    "uncertain_language": "I couldn't confidently tell what language was spoken. Please try again.",
}

# --- Pydantic Schemas ---
class WhatsAppTextPayload(BaseModel):
    user_id: str
    message_id: Optional[str] = None
    message: str
    source: str = "whatsapp"
    input_type: str = "text"

class TicketResolutionRequest(BaseModel):
    agent_id: str = "human_support_lead"
    resolution_text: str

class SimulatorRequest(BaseModel):
    query: str
    use_voice_sim: bool = False
    language_mode: str = "auto"

class CustomerRegisterPayload(BaseModel):
    full_name: str
    phone_number: str
    email: str
    password: str
    account_type: str = "Prepaid"

class CustomerLoginPayload(BaseModel):
    email_or_phone: str
    password: str

class CustomerMobileQueryPayload(BaseModel):
    customer_id: str
    query: str

class ServiceFeedbackPayload(BaseModel):
    customer_id: str
    rating: int
    comments: Optional[str] = ""

# Helper to dispatch WhatsApp sign-in notification automatically
def send_whatsapp_signin_alert(phone_number: str, customer_name: str, is_new_register: bool = False, session_id: str = ""):
    """Automated WhatsApp message sent ONLY when a customer signs in or registers."""
    try:
        clean = phone_number.replace("+", "").replace(" ", "").replace("-", "")
        if len(clean) == 10:
            clean = "91" + clean
        target = f"{clean}@c.us" if not clean.endswith("@c.us") else clean
        action_type = "Registration Successful! 🎉" if is_new_register else "Sign-In Verified 🔐"
        
        session_line = f"\n🔑 *Session ID:* `{session_id}`" if session_id else ""
        msg = (
            f"📱 *Telecom Mobile App - {action_type}*\n\n"
            f"Hello *{customer_name}*,\n\n"
            f"You have successfully authenticated into the Telecom Mobile Application.{session_line}\n\n"
            f"✨ *Greetings:* Welcome to Telecom AI Customer Care! How can we assist you today?\n\n"
            f"💬 Simply type your query or send a voice message here — our AI will analyze, categorize, and resolve it instantly!"
        )
        data = json.dumps({"to": target, "message": msg, "raw": True}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:3001/send-message",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            print(f"[WhatsApp Automation] Dispatched automated sign-in notification to {target} (session: {session_id})")
            return True
    except Exception as err:
        print(f"[WhatsApp Automation Note] WhatsApp gateway dispatch skipped/offline: {err}")
        return False

def send_whatsapp_query_result(
    phone_number: str,
    customer_name: str,
    query: str,
    category: str,
    sub_category: str,
    sentiment: str,
    priority: str,
    solution: str,
    recommended_action: str,
    status: str,
    session_id: str = "",
    frequency_count: int = 1
):
    """Auto-dispatches WhatsApp message with full RAG query analysis after every customer query from the mobile app."""
    try:
        clean = phone_number.replace("+", "").replace(" ", "").replace("-", "")
        if len(clean) == 10:
            clean = "91" + clean
        target = f"{clean}@c.us" if not clean.endswith("@c.us") else clean

        # Status label
        if status == "escalated_to_human":
            status_line = "🚨 *Status:* ESCALATED to Senior Support"
        else:
            status_line = "✅ *Status:* RESOLVED by AI Engine"

        # Sentiment emoji
        sentiment_emoji = {"Negative": "😠", "Positive": "😊", "Neutral": "😐"}.get(sentiment, "😐")

        # Priority emoji
        priority_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(priority, "🟡")

        # Frequency note
        freq_note = ""
        if frequency_count > 1:
            freq_note = f"\n⚠️ *Repeat Occurrence:* {frequency_count}x (Auto-priority escalated)"

        session_line = f"\n🔑 *Session:* `{session_id}`" if session_id else ""

        clean_solution = solution.replace("#", "").replace("**", "*").strip()
        clean_rec = recommended_action.replace("#", "").strip() if recommended_action else ""

        msg = (
            f"📊 *Telecom AI — Query Analysis Result*\n"
            f"──────────────────────\n\n"
            f"👤 Hello *{customer_name}*, your query has been analysed:\n\n"
            f"💬 *Query:* {query[:120]}{'...' if len(query) > 120 else ''}\n\n"
            f"📂 *Category:* {category} › {sub_category}\n"
            f"{sentiment_emoji} *Sentiment:* {sentiment}\n"
            f"{priority_emoji} *Priority:* {priority}\n"
            f"{freq_note}\n"
            f"──────────────────────\n"
            f"💡 *AI Solution:*\n{clean_solution}\n\n"
            f"🚀 *Recommended Action:*\n{clean_rec}\n\n"
            f"{status_line}"
            f"{session_line}"
        )

        data = json.dumps({"to": target, "message": msg, "raw": True}).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:3001/send-message",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            print(f"[WhatsApp Automation] Dispatched query analysis result to {target}")
            return True
    except Exception as err:
        print(f"[WhatsApp Automation Note] Query result dispatch skipped/offline: {err}")
        return False

# ==========================================
# MOBILE APPLICATION AUTHENTICATION & QUERY ENDPOINTS (POSTGRESQL PERSISTED)
# ==========================================

@app.post("/api/auth/register")
def mobile_register(payload: CustomerRegisterPayload):
    """Registers a new customer in PostgreSQL DB and dispatches automated WhatsApp sign-in greeting."""
    try:
        cust = db.register_customer(
            full_name=payload.full_name,
            phone_number=payload.phone_number,
            email=payload.email,
            password=payload.password,
            account_type=payload.account_type
        )
        # Send automated WhatsApp message ONLY to sign-in / registration
        send_whatsapp_signin_alert(cust["phone_number"], cust["full_name"], is_new_register=True, session_id=cust.get("session_id", ""))
        
        greetings = f"Hello {cust['full_name']}! Welcome to Telecom AI Customer Care 👋 How can we assist you with your {cust['account_type']} connection today?"
        return {
            "status": "success",
            "message": "Account created successfully and stored in PostgreSQL DB.",
            "customer": cust,
            "token": cust.get("token", f"JWT-SIM-{cust['id']}"),
            "session_id": cust.get("session_id", ""),
            "greetings": greetings,
            "whatsapp_automated": True
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Registration error: {str(err)}")

@app.post("/api/auth/login")
def mobile_login(payload: CustomerLoginPayload):
    """Authenticates customer against PostgreSQL DB and dispatches automated WhatsApp sign-in alert."""
    try:
        cust = db.login_customer(
            email_or_phone=payload.email_or_phone,
            password=payload.password
        )
        # Send automated WhatsApp message ONLY to sign-in
        send_whatsapp_signin_alert(cust["phone_number"], cust["full_name"], is_new_register=False, session_id=cust.get("session_id", ""))
        
        greetings = f"Welcome back, {cust['full_name']}! 👋 We are ready to process your query."
        return {
            "status": "success",
            "message": "Authenticated successfully via PostgreSQL DB.",
            "customer": cust,
            "token": cust.get("token", f"JWT-SIM-{cust['id']}"),
            "session_id": cust.get("session_id", ""),
            "greetings": greetings,
            "whatsapp_automated": True
        }
    except ValueError as val_err:
        raise HTTPException(status_code=401, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Login error: {str(err)}")

def format_executive_rag_response(
    query: str,
    category: str,
    sub_category: str,
    raw_ai_response: str,
    frequency_count: int,
    sentiment: str = "Neutral"
) -> Dict[str, Any]:
    """
    Constructs a highly relevant Executive RAG Response containing:
    1. Executive Summary of Problem
    2. Category & Sub-Category
    3. Issue Description
    4. Solution
    5. Recommended Action (Dynamic escalation driven by PostgreSQL frequency count)
    """
    q_lower = query.lower()
    
    # 1. Executive Summary
    if "5g" in q_lower or "network" in q_lower or "tower" in q_lower:
        exec_summary = f"Degradation of 5G cellular network connectivity and data throughput reported under {category} ({sub_category})."
    elif "bill" in q_lower or "charge" in q_lower or "extra" in q_lower or "cost" in q_lower:
        exec_summary = f"Billing dispute regarding an unexpected charge line-item under {category} ({sub_category})."
    elif "roam" in q_lower or "international" in q_lower:
        exec_summary = f"Service provisioning request for International Roaming pack activation under {category} ({sub_category})."
    else:
        exec_summary = f"Customer reported service query regarding '{query[:70]}...' classified under {category} ({sub_category})."

    # 2. Issue Description
    issue_description = (
        f"Query: '{query}'. Detected Sentiment: {sentiment.upper()}. "
        f"Customer query frequency for this category in PostgreSQL DB: {frequency_count} occurrence(s)."
    )

    # 3. Clean Solution
    solution = raw_ai_response.strip() if raw_ai_response else f"Apply standard self-service RAG procedure for {sub_category}."
    solution = solution.replace("#", "")

    # 4. Recommended Action (DYNAMIC BASED ON FREQUENCY)
    if frequency_count == 1:
        rec_action = (
            f"ℹ️ [Standard Resolution - 1st Occurrence]: "
            f"Provide automated self-service resolution guide. Monitor line telemetry for 24 hours. "
            f"No supervisor escalation required."
        )
    elif frequency_count == 2:
        rec_action = (
            f"⚠️ [Repeat Issue Escalation - 2nd Occurrence]: "
            f"Repeat issue detected (Count: 2). SLA priority automatically bumped to HIGH. "
            f"Schedule a proactive senior support check-in within 2 hours."
        )
    else:
        rec_action = (
            f"🚨 [CRITICAL CHRONIC ESCALATION - {frequency_count} Occurrences]: "
            f"Chronic issue detected ({frequency_count} repeated occurrences in PostgreSQL DB). "
            f"Automatically dispatch a Field Technician for site audit and issue a $15 billing credit waiver."
        )

    formatted_md = (
        f"📌 **EXECUTIVE SUMMARY OF PROBLEM**\n{exec_summary}\n\n"
        f"📂 **CATEGORY & SUB-CATEGORY**\nCategory: `{category}` | Sub-Category: `{sub_category}`\n\n"
        f"🔍 **ISSUE DESCRIPTION**\n{issue_description}\n\n"
        f"💡 **SOLUTION**\n{solution}\n\n"
        f"🚀 **RECOMMENDED ACTION** (Frequency: {frequency_count}x)\n{rec_action}"
    )

    return {
        "executive_summary": exec_summary,
        "category": category,
        "sub_category": sub_category,
        "issue_description": issue_description,
        "solution": solution,
        "recommended_action": rec_action,
        "frequency_count": frequency_count,
        "formatted_markdown": formatted_md
    }

@app.post("/api/mobile/query/text")
def mobile_query_text(payload: CustomerMobileQueryPayload):
    """Analyzes customer text query from Mobile App using LangGraph Orchestration & persists in PostgreSQL DB."""
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Fetch the customer's active session_id to link the query record to the session
    session_id = db.get_latest_session(payload.customer_id) if hasattr(db, "get_latest_session") else ""

    pipeline_out = orchestrator.run(
        query=query,
        user_id=payload.customer_id,
        use_local_llm=True,
        evaluate_response=False
    )

    cat = pipeline_out.get("category", "General")
    sub_cat = pipeline_out.get("sub_category", "Support")
    sentiment = pipeline_out.get("sentiment", "Neutral")
    priority = pipeline_out.get("priority", "Medium")
    raw_ai_resp = pipeline_out.get("response", "")
    steps = pipeline_out.get("orchestration_steps", [])
    is_escalated = pipeline_out.get("escalated_to_human", False)

    # Calculate occurrence frequency in PostgreSQL DB for dynamic recommendation
    freq_count = db.get_query_frequency(payload.customer_id, cat) if hasattr(db, "get_query_frequency") else 1
    final_priority = "High" if freq_count >= 2 else priority
    final_status = "escalated_to_human" if (is_escalated or freq_count >= 2) else "resolved"

    # Format structured Executive RAG Response
    exec_struct = format_executive_rag_response(
        query=query,
        category=cat,
        sub_category=sub_cat,
        raw_ai_response=raw_ai_resp,
        frequency_count=freq_count,
        sentiment=sentiment
    )

    # Save record in PostgreSQL DB — now includes session_id + resolved category + status
    db_rec = db.save_customer_query(
        customer_id=payload.customer_id,
        input_type="text",
        raw_query=query,
        transcript=query,
        english_translation=query,
        category=cat,
        sub_category=sub_cat,
        sentiment=sentiment,
        priority=final_priority,
        ai_response=exec_struct["formatted_markdown"],
        orchestration_steps=steps,
        status=final_status,
        session_id=session_id
    )

    # Auto-dispatch WhatsApp message with full analysis to customer's registered phone
    cust = (db.get_customer_by_id(payload.customer_id) or db.get_customer_by_phone(payload.customer_id)) if hasattr(db, "get_customer_by_id") else None
    if cust and cust.get("phone_number"):
        send_whatsapp_query_result(
            phone_number=cust["phone_number"],
            customer_name=cust["full_name"],
            query=query,
            category=cat,
            sub_category=sub_cat,
            sentiment=sentiment,
            priority=final_priority,
            solution=exec_struct["solution"],
            recommended_action=exec_struct["recommended_action"],
            status=final_status,
            session_id=session_id,
            frequency_count=freq_count
        )

    return {
        "status": "success",
        "query_record": db_rec,
        "session_id": session_id,
        "category": cat,
        "sub_category": sub_cat,
        "sentiment": sentiment,
        "priority": final_priority,
        "response": exec_struct["formatted_markdown"],
        "executive_summary": exec_struct["executive_summary"],
        "issue_description": exec_struct["issue_description"],
        "solution": exec_struct["solution"],
        "recommended_action": exec_struct["recommended_action"],
        "frequency_count": freq_count,
        "escalated_to_human": is_escalated or (freq_count >= 2),
        "query_resolved_category": cat,
        "query_status": final_status,
        "whatsapp_notified": True,
        "orchestration_steps": steps
    }

@app.post("/api/service/complete")
def mobile_service_complete(payload: ServiceFeedbackPayload):
    """Saves customer feedback rating in PostgreSQL DB, returns post-service Thank You message, and dispatches a clean WhatsApp service summary."""
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5.")
        
    fb_rec = db.save_service_feedback(
        customer_id=payload.customer_id,
        rating=payload.rating,
        comments=payload.comments or ""
    )
    
    # Fetch latest query for the customer to show the summary of service resolution (without hashtags)
    queries = db.get_customer_queries(payload.customer_id)
    latest_query = queries[0] if queries else None
    output_description = latest_query["ai_response"] if latest_query else ""
    if output_description:
        output_description = output_description.replace("#", "").strip()
        
    thank_you_message = (
        "🙏 Thank You for choosing Telecom AI Customer Services! "
        "We are glad to have assisted you today. Your valuable feedback has been recorded in our PostgreSQL Database. "
        "Have a wonderful day!"
    )
    
    # Send automated WhatsApp message on service completion
    whatsapp_dispatched = False
    cust = db.get_customer_by_id(payload.customer_id)
    if cust and cust.get("phone_number") and output_description:
        phone_number = cust["phone_number"]
        clean = phone_number.replace("+", "").replace(" ", "").replace("-", "")
        if len(clean) == 10:
            clean = "91" + clean
        target = f"{clean}@c.us" if not clean.endswith("@c.us") else clean
        
        # Clean service end message formatted nicely
        msg = (
            f"✅ *Service Completed & Feedback Recorded*\n\n"
            f"Dear *{cust['full_name']}*,\n\n"
            f"Thank you for your rating of {payload.rating}/5! We have successfully completed your service request.\n\n"
            f"📋 *Service Output Description:*\n{output_description}"
        )
        
        try:
            import urllib.request
            import json
            req_data = json.dumps({
                "to": target,
                "message": msg,
                "raw": True
            }).encode("utf-8")
            
            req = urllib.request.Request(
                "http://127.0.0.1:3001/send-message",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                if resp.status == 200:
                    whatsapp_dispatched = True
                    print(f"[WhatsApp Automation] Dispatched automated service complete alert to {target}")
        except Exception as e:
            print(f"[Notice] Could not dispatch service complete alert to WhatsApp: {e}")
            
    return {
        "status": "success",
        "feedback": fb_rec,
        "thank_you_message": thank_you_message,
        "output_description": output_description,
        "whatsapp_dispatched": whatsapp_dispatched
    }

@app.get("/api/customer/queries")
def mobile_customer_queries(customer_id: str = Query(...)):
    """Fetches customer query history from PostgreSQL DB."""
    queries = db.get_customer_queries(customer_id)
    return {"status": "success", "customer_id": customer_id, "queries": queries}


# ==========================================
# WHATSAPP GATEWAY INTEGRATION ENDPOINTS
# ==========================================

@app.post("/api/whatsapp/message")
def handle_whatsapp_message(payload: WhatsAppTextPayload):
    """Processes incoming text messages from WhatsApp Gateway via LangGraph pipeline for registered users."""
    query = payload.message.strip()
    user_id = payload.user_id
    
    if not query:
        return {"status": "error", "response": "Empty message received."}

    # Verify if sender is an active registered user in PostgreSQL DB
    cust = db.get_customer_by_phone(user_id) if hasattr(db, "get_customer_by_phone") else None
    if not cust:
        return {
            "status": "unauthorized",
            "response": (
                "🔒 *Telecom AI Customer Care — Access Restricted*\n\n"
                "Hello! Automated WhatsApp AI support is active exclusively for registered Telecom Mobile App users.\n\n"
                "📱 *How to access:*\n"
                "1. Open the Telecom Mobile App on your device.\n"
                "2. Sign in or register with this phone number.\n"
                "3. Your account will automatically unlock 24/7 AI WhatsApp care!"
            )
        }

    customer_db_id = cust["id"]
    customer_name = cust["full_name"]

    # Execute complete LangGraph Orchestration Pipeline
    pipeline_out = orchestrator.run(
        query=query,
        user_id=customer_db_id,
        use_local_llm=True,
        evaluate_response=True
    )

    ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
    is_escalated = pipeline_out.get("escalated_to_human", False)
    cat = pipeline_out.get("category", "General")
    sub_cat = pipeline_out.get("sub_category", "Support")
    sentiment = pipeline_out.get("sentiment", "Neutral")
    priority = pipeline_out.get("priority", "Medium")
    raw_ai_resp = pipeline_out.get("response", "")
    steps = pipeline_out.get("orchestration_steps", [])

    # Format structured Executive RAG Response & calculate frequency
    freq_count = db.get_query_frequency(customer_db_id, cat) if hasattr(db, "get_query_frequency") else 1
    exec_struct = format_executive_rag_response(
        query=query,
        category=cat,
        sub_category=sub_cat,
        raw_ai_response=raw_ai_resp,
        frequency_count=freq_count,
        sentiment=sentiment
    )
    
    # Fetch active session_id to link WhatsApp query to the customer's last login session
    wa_session_id = db.get_latest_session(customer_db_id) if hasattr(db, "get_latest_session") else ""
    wa_final_priority = "High" if freq_count >= 2 else priority
    wa_final_status = "escalated_to_human" if (is_escalated or freq_count >= 2) else "resolved"

    # Store in persistent PostgreSQL DB so it automatically reflects in the Mobile App
    try:
        db.save_customer_query(
            customer_id=customer_db_id,
            input_type="whatsapp_text",
            raw_query=query,
            transcript=query,
            english_translation=query,
            category=cat,
            sub_category=sub_cat,
            sentiment=sentiment,
            priority=wa_final_priority,
            ai_response=exec_struct["formatted_markdown"],
            orchestration_steps=steps,
            status=wa_final_status,
            session_id=wa_session_id
        )
    except Exception as db_err:
        print(f"[DB Sync Note] Could not save WhatsApp query to customer history: {db_err}")

    # Store ticket in live dashboard DB
    ticket_record = {
        "id": ticket_id,
        "user_id": f"{customer_name} ({user_id})",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "input_type": "text",
        "raw_transcript": query,
        "english_translation": query,
        "category": cat,
        "sub_category": sub_cat,
        "sentiment": sentiment,
        "emotion": pipeline_out.get("emotion", "Calm"),
        "priority": priority,
        "priority_score": pipeline_out.get("priority_score", 5.0),
        "status": "escalated_to_human" if (is_escalated or freq_count >= 2) else "resolved_by_ai",
        "escalated_to_human": is_escalated or (freq_count >= 2),
        "tools_called": pipeline_out.get("tools_called", []),
        "tool_results": pipeline_out.get("tool_results", {}),
        "ai_response": raw_ai_resp,
        "human_resolution": None,
        "resolved_at": None
    }
    tickets_db.insert(0, ticket_record)

    # Format reply text for WhatsApp customer with continuous loop prompt
    if is_escalated or freq_count >= 2:
        response_text = (
            f"Hello *{customer_name}*,\n\n"
            f"⚠️ *Support Escalation Alert*\n\n"
            f"{raw_ai_resp}\n\n"
            f"📌 *Status:* Escalated to Senior Support (Priority: HIGH)\n"
            f"A representative will review your case.\n\n"
            f"💬 *Have another query?* Just send another message or voice note anytime!"
        )
    else:
        response_text = (
            f"Hello *{customer_name}*,\n\n"
            f"{raw_ai_resp}\n\n"
            f"💬 *Have another query?* You can ask again anytime!"
        )

    return {
        "status": "ok",
        "ticket_id": ticket_id,
        "response": response_text,
        "category": cat,
        "sentiment": sentiment,
        "priority": priority,
        "tools_called": pipeline_out.get("tools_called", []),
        "tool_results": pipeline_out.get("tool_results", {}),
        "escalated_to_human": is_escalated
    }


@app.post("/api/whatsapp/voice")
async def handle_whatsapp_voice(
    audio: UploadFile = File(...),
    user_id: str = Form(...),
    message_id: Optional[str] = Form(None)
):
    """Processes incoming voice notes from WhatsApp Gateway via Speech-to-Text for registered users."""
    try:
        # Verify if sender is an active registered user in PostgreSQL DB
        cust = db.get_customer_by_phone(user_id) if hasattr(db, "get_customer_by_phone") else None
        if not cust:
            return {
                "status": "unauthorized",
                "transcription": "",
                "response": (
                    "🔒 *Telecom AI Voice Assistant — Access Restricted*\n\n"
                    "Hello! Automated voice AI assistance is enabled exclusively for registered Telecom Mobile App users.\n\n"
                    "Please sign in on the Telecom Mobile App with this number to activate automatic voice assistance."
                ),
                "escalated_to_human": False
            }

        customer_db_id = cust["id"]
        customer_name = cust["full_name"]

        # Save temporary audio file
        ext = audio.filename.split(".")[-1] if "." in audio.filename else "ogg"
        saved_filename = f"{int(time.time())}_{uuid.uuid4().hex[:6]}.{ext}"
        saved_filepath = os.path.join(AUDIO_DIR, saved_filename)

        with open(saved_filepath, "wb") as f:
            content = await audio.read()
            f.write(content)

        # Stage 1: Noise reduction & Speech-to-Text via Whisper
        cleaned_path = clean_audio(saved_filepath)
        stt_result = transcribe_speech(cleaned_path, language_mode="auto")

        raw_transcript = stt_result.get("text", "")
        if not stt_result.get("is_reliable", True) or not raw_transcript.strip():
            fallback_msg = STT_RETRY_MESSAGES.get(
                stt_result.get("reason", ""),
                "Could not hear speech clearly. Please try sending your voice note again."
            )
            return {
                "status": "retry",
                "transcription": "",
                "response": fallback_msg,
                "escalated_to_human": False
            }

        # Stage 2: Translate non-English voice transcript to English for ML models
        translated = transcribe_to_english(cleaned_path)
        english_text = translated.get("english_text", raw_transcript)

        # Stage 3: Pass into LangGraph Orchestrator
        pipeline_out = orchestrator.run(
            query=english_text,
            user_id=customer_db_id,
            use_local_llm=True,
            evaluate_response=True
        )

        ticket_id = f"TICK-{uuid.uuid4().hex[:6].upper()}"
        is_escalated = pipeline_out.get("escalated_to_human", False)
        cat = pipeline_out.get("category", "General")
        sub_cat = pipeline_out.get("sub_category", "Support")
        sentiment = pipeline_out.get("sentiment", "Neutral")
        priority = pipeline_out.get("priority", "Medium")
        raw_ai_resp = pipeline_out.get("response", "")
        steps = pipeline_out.get("orchestration_steps", [])

        # Format structured Executive RAG Response
        freq_count = db.get_query_frequency(customer_db_id, cat) if hasattr(db, "get_query_frequency") else 1
        exec_struct = format_executive_rag_response(
            query=english_text,
            category=cat,
            sub_category=sub_cat,
            raw_ai_response=raw_ai_resp,
            frequency_count=freq_count,
            sentiment=sentiment
        )

        # Store in persistent PostgreSQL DB so it automatically reflects in the Mobile App
        try:
            db.save_customer_query(
                customer_id=customer_db_id,
                input_type="whatsapp_voice",
                raw_query=raw_transcript,
                transcript=raw_transcript,
                english_translation=english_text,
                category=cat,
                sub_category=sub_cat,
                sentiment=sentiment,
                priority="High" if freq_count >= 2 else priority,
                ai_response=exec_struct["formatted_markdown"],
                orchestration_steps=steps,
                status="escalated_to_human" if (is_escalated or freq_count >= 2) else "resolved"
            )
        except Exception as db_err:
            print(f"[DB Sync Note] Could not save WhatsApp voice query to customer history: {db_err}")

        ticket_record = {
            "id": ticket_id,
            "user_id": f"{customer_name} ({user_id})",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "input_type": "voice",
            "raw_transcript": raw_transcript,
            "english_translation": english_text,
            "category": cat,
            "sub_category": sub_cat,
            "sentiment": sentiment,
            "emotion": pipeline_out.get("emotion", "Calm"),
            "priority": priority,
            "priority_score": pipeline_out.get("priority_score", 5.0),
            "status": "escalated_to_human" if (is_escalated or freq_count >= 2) else "resolved_by_ai",
            "escalated_to_human": is_escalated or (freq_count >= 2),
            "tools_called": pipeline_out.get("tools_called", []),
            "tool_results": pipeline_out.get("tool_results", {}),
            "ai_response": raw_ai_resp,
            "human_resolution": None,
            "resolved_at": None
        }
        tickets_db.insert(0, ticket_record)

        ai_response = f"Hello *{customer_name}*,\n\n{raw_ai_resp}\n\n💬 *Have another query?* Just send another voice note or message!"

        return {
            "status": "ok",
            "ticket_id": ticket_id,
            "transcription": raw_transcript,
            "english_translation": english_text,
            "response": ai_response,
            "category": cat,
            "sentiment": sentiment,
            "priority": priority,
            "tools_called": pipeline_out.get("tools_called", []),
            "tool_results": pipeline_out.get("tool_results", {}),
            "escalated_to_human": is_escalated
        }

    except Exception as e:
        print(f"Error handling WhatsApp voice note: {e}")
        return {
            "status": "error",
            "transcription": "",
            "response": f"Sorry, an error occurred while processing your voice note: {str(e)}"
        }


@app.post("/api/process-audio")
async def process_mobile_audio(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    language_mode: str = Form("auto")
):
    """Processes audio uploaded from Telecom Mobile App (Speech-To-Text + LangGraph + DB persistence)."""
    try:
        temp_dir = BACKEND_DIR / "audio_input"
        temp_dir.mkdir(exist_ok=True)
        fname = file.filename or "voice_query.m4a"
        ext = fname.split(".")[-1] if "." in fname else "m4a"
        saved_path = temp_dir / f"mob_{int(time.time())}_{uuid.uuid4().hex[:6]}.{ext}"

        content = await file.read()
        if not content or len(content) == 0:
            return {
                "status": "retry",
                "transcription": "",
                "response": "No audio recorded or received. Please record again.",
                "escalated_to_human": False
            }

        with open(saved_path, "wb") as f:
            f.write(content)

        cleaned_path = clean_audio(str(saved_path))
        stt_result = transcribe_speech(cleaned_path, language_mode=language_mode)
        raw_transcript = stt_result.get("text", "")

        if not stt_result.get("is_reliable", True) or not raw_transcript.strip():
            fallback_msg = STT_RETRY_MESSAGES.get(
                stt_result.get("reason", ""),
                "Could not hear speech clearly. Please speak closer to the microphone and try again."
            )
            return {
                "status": "retry",
                "transcription": "",
                "response": fallback_msg,
                "escalated_to_human": False
            }

        translated = transcribe_to_english(cleaned_path)
        english_text = translated.get("english_text", raw_transcript)

        # Run through LangGraph Orchestrator
        pipeline_out = orchestrator.run(
            query=english_text,
            user_id=user_id,
            use_local_llm=True,
            evaluate_response=True
        )

        cat = pipeline_out.get("category", "General")
        sub_cat = pipeline_out.get("sub_category", "Support")
        sentiment = pipeline_out.get("sentiment", "Neutral")
        priority = pipeline_out.get("priority", "Medium")
        raw_ai_resp = pipeline_out.get("response", "")
        steps = pipeline_out.get("orchestration_steps", [])

        freq_count = db.get_query_frequency(user_id, cat) if hasattr(db, "get_query_frequency") else 1
        exec_struct = format_executive_rag_response(
            query=english_text,
            category=cat,
            sub_category=sub_cat,
            raw_ai_response=raw_ai_resp,
            frequency_count=freq_count,
            sentiment=sentiment
        )

        # Persist in DB
        try:
            db.save_customer_query(
                customer_id=user_id,
                input_type="voice",
                raw_query=raw_transcript,
                transcript=raw_transcript,
                english_translation=english_text,
                category=cat,
                sub_category=sub_cat,
                sentiment=sentiment,
                priority="High" if freq_count >= 2 else priority,
                ai_response=exec_struct["formatted_markdown"],
                orchestration_steps=steps,
                status="escalated_to_human" if (pipeline_out.get("escalated_to_human") or freq_count >= 2) else "resolved"
            )
        except Exception as db_err:
            print(f"[DB Sync Note] Could not save mobile voice query to customer history: {db_err}")

        # Auto-dispatch WhatsApp message to registered customer phone if available
        cust = (db.get_customer_by_id(user_id) or db.get_customer_by_phone(user_id)) if hasattr(db, "get_customer_by_id") else None
        if cust and cust.get("phone_number"):
            send_whatsapp_query_result(
                phone_number=cust["phone_number"],
                customer_name=cust["full_name"],
                query=raw_transcript,
                category=cat,
                sub_category=sub_cat,
                sentiment=sentiment,
                priority="High" if freq_count >= 2 else priority,
                solution=exec_struct["solution"],
                recommended_action=exec_struct["recommended_action"],
                status="escalated_to_human" if (pipeline_out.get("escalated_to_human") or freq_count >= 2) else "resolved",
                frequency_count=freq_count
            )

        return {
            "status": "ok",
            "transcription": raw_transcript,
            "english_translation": english_text,
            "response": exec_struct["formatted_markdown"],
            "executive_summary": exec_struct["executive_summary"],
            "issue_description": exec_struct["issue_description"],
            "solution": exec_struct["solution"],
            "recommended_action": exec_struct["recommended_action"],
            "category": cat,
            "sub_category": sub_cat,
            "sentiment": sentiment,
            "priority": "High" if freq_count >= 2 else priority,
            "frequency_count": freq_count,
            "escalated_to_human": pipeline_out.get("escalated_to_human", False) or (freq_count >= 2)
        }
    except Exception as e:
        print(f"Error processing mobile audio: {e}")
        return {
            "status": "error",
            "transcription": "",
            "response": f"Audio processing error: {str(e)}"
        }


@app.post("/speech-to-text")
def speech_to_text_endpoint(language_mode: str = Form("auto"), duration: int = Form(6)):
    """Direct Server Microphone Recording & Pipeline (matching Sahaya Voice UI)."""
    try:
        raw_path = record_audio(duration=duration)
        clean_path = clean_audio(raw_path)

        # Stage 1: STT
        result = transcribe_speech(clean_path, language_mode=language_mode)
        if not result.get("is_reliable", True) or not result.get("text", "").strip():
            reason = result.get("reason", "no_speech_detected")
            msg = STT_RETRY_MESSAGES.get(reason, "Could not hear speech clearly. Please try again.")
            audio_url = None
            try:
                speak_text(msg, language="english")
                audio_url = "/audio/response.mp3"
            except Exception:
                pass
            return {
                "status": "retry",
                "reason": reason,
                "message": msg,
                "raw_transcript": result.get("text", ""),
                "audio_url": audio_url,
                "confidence_stats": result.get("confidence_stats", {})
            }

        # Stage 2: Intent understanding / text correction
        if understand_transcript:
            understanding = understand_transcript(result["text"], language_hint=result.get("detected_language", "english"))
        else:
            understanding = {"text": result["text"], "understood": True}

        # Stage 3: Translate to English
        translated = transcribe_to_english(clean_path)
        english_text = translated.get("english_text") or understanding["text"]

        # Stage 4: LangGraph pipeline execution
        pipeline_out = orchestrator.run(
            query=english_text,
            use_local_llm=True,
            evaluate_response=True
        )

        ai_resp = pipeline_out.get("response", "")
        audio_url = None
        try:
            speak_text(ai_resp, language="english")
            audio_url = "/audio/response.mp3"
        except Exception:
            pass

        return {
            "status": "ok",
            "detected_language": result.get("detected_language", "en"),
            "raw_transcript": result.get("text", ""),
            "corrected_transcript": understanding["text"],
            "english_translation": english_text,
            "confidence": result.get("confidence", 0.95),
            "confidence_stats": result.get("confidence_stats", {}),
            "sentiment": pipeline_out.get("sentiment", "Neutral"),
            "sentiment_confidence": pipeline_out.get("sentiment_confidence", 0.85),
            "emotion": pipeline_out.get("emotion", "Calm"),
            "emotion_confidence": pipeline_out.get("emotion_confidence", 0.85),
            "category": pipeline_out.get("category", "General"),
            "sub_category": pipeline_out.get("sub_category", "Support"),
            "priority": pipeline_out.get("priority", "Medium"),
            "priority_score": pipeline_out.get("priority_score", 5.0),
            "priority_rank": pipeline_out.get("priority_rank", 2),
            "ai_response": ai_resp,
            "audio_url": audio_url,
            "escalated_to_human": pipeline_out.get("escalated_to_human", False)
        }
    except Exception as e:
        print(f"Error in speech-to-text: {e}")
        return {"status": "error", "message": str(e)}


# ==========================================
# EXECUTIVE UI DASHBOARD ENDPOINTS
# ==========================================

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    """Returns high-level non-technical executive KPIs and analytics."""
    total = len(tickets_db)
    escalated = sum(1 for t in tickets_db if t.get("escalated_to_human"))
    resolved_ai = total - escalated
    resolution_rate = round((resolved_ai / total * 100), 1) if total > 0 else 100.0

    voice_count = sum(1 for t in tickets_db if t.get("input_type") == "voice")
    text_count = total - voice_count

    # Sentiment distribution
    sentiments = {"Positive": 0, "Neutral": 0, "Negative": 0}
    for t in tickets_db:
        s = t.get("sentiment", "Neutral")
        sentiments[s] = sentiments.get(s, 0) + 1

    # Category distribution
    categories = {}
    for t in tickets_db:
        c = t.get("category", "General")
        categories[c] = categories.get(c, 0) + 1

    # Priority distribution
    priorities = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for t in tickets_db:
        p = t.get("priority", "Medium")
        priorities[p] = priorities.get(p, 0) + 1

    return {
        "total_queries": total,
        "ai_resolved_count": resolved_ai,
        "escalated_count": escalated,
        "ai_resolution_rate": resolution_rate,
        "avg_response_time_sec": 1.4,
        "channel_mix": {
            "voice": voice_count,
            "text": text_count
        },
        "sentiment_distribution": sentiments,
        "category_distribution": categories,
        "priority_distribution": priorities
    }


@app.get("/api/dashboard/tickets")
def get_dashboard_tickets(filter_type: str = Query("all")):
    """Returns list of tickets for live conversation feed & escalation desk."""
    if filter_type == "escalated":
        filtered = [t for t in tickets_db if t.get("escalated_to_human")]
    elif filter_type == "resolved":
        filtered = [t for t in tickets_db if not t.get("escalated_to_human")]
    else:
        filtered = tickets_db

    return {"tickets": filtered, "count": len(filtered)}


@app.post("/api/dashboard/tickets/{ticket_id}/resolve")
def resolve_ticket(ticket_id: str, payload: TicketResolutionRequest):
    """Allows a human support agent to manually resolve an escalated ticket and dispatch to WhatsApp."""
    target = None
    for t in tickets_db:
        if t["id"] == ticket_id:
            target = t
            break

    if not target:
        raise HTTPException(status_code=404, detail="Ticket not found.")

    target["status"] = "resolved_by_human"
    target["escalated_to_human"] = False
    target["human_resolution"] = payload.resolution_text
    target["resolved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

    # Attempt to dispatch message back to customer on WhatsApp via Gateway listener port 3001
    whatsapp_dispatched = False
    try:
        import urllib.request
        import json
        req_data = json.dumps({
            "to": target.get("user_id"),
            "message": payload.resolution_text
        }).encode("utf-8")
        
        req = urllib.request.Request(
            "http://127.0.0.1:3001/send-message",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                whatsapp_dispatched = True
    except Exception as e:
        print(f"[Notice] Could not dispatch to WhatsApp listener (Gateway offline or unauthenticated): {e}")

    return {
        "status": "ok",
        "message": f"Ticket {ticket_id} resolved by {payload.agent_id}.",
        "whatsapp_dispatched": whatsapp_dispatched,
        "ticket": target
    }


@app.post("/api/dashboard/simulator")
def run_pipeline_simulator(payload: SimulatorRequest):
    """Interactive sandbox endpoint to test full WP -> STT -> LangGraph RAG flow."""
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    pipeline_out = orchestrator.run(
        query=query,
        user_id="simulated_user",
        use_local_llm=True,
        evaluate_response=True
    )

    return {
        "status": "ok",
        "pipeline_result": pipeline_out
    }


# Standard legacy audio endpoints
@app.post("/speech-to-text")
def speech_to_text(language_mode: str = Form("auto"), duration: int = Form(6)):
    raw_path = record_audio(duration=duration)
    clean_path = clean_audio(raw_path)
    result = transcribe_speech(clean_path, language_mode=language_mode)

    if not result["is_reliable"]:
        return {
            "status": "retry",
            "reason": result["reason"],
            "message": STT_RETRY_MESSAGES.get(result["reason"], "Could not hear speech clearly."),
            "raw_transcript": result["text"]
        }

    translated = transcribe_to_english(clean_path)
    pipeline_out = orchestrator.run(query=translated["english_text"])

    return {
        "status": "ok",
        "detected_language": result["detected_language"],
        "raw_transcript": result["text"],
        "english_translation": translated["english_text"],
        "confidence": result["confidence"],
        "sentiment": pipeline_out.get("sentiment"),
        "category": pipeline_out.get("category"),
        "priority": pipeline_out.get("priority"),
        "response": pipeline_out.get("response")
    }


@app.post("/text-to-speech")
def text_to_speech(text: str = Form(...), language: str = Form("english")):
    speak_text(text, language=language)
    return {"status": "spoken", "text": text, "audio_url": "/audio/response.mp3"}


# ==========================================
# STANDALONE TRANSCRIPTION ENDPOINT
# ==========================================

@app.post("/api/transcribe")
async def transcribe_audio_file(
    file: UploadFile = File(...),
    language_mode: str = Form("auto")
):
    """
    Upload audio file (WAV/MP3/OGG) → Noise Reduction → Whisper STT → English Translation.
    Returns raw transcript, detected language, confidence, and English translation.
    """
    import shutil
    temp_dir = BACKEND_DIR / "audio_input"
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"upload_{int(time.time())}_{file.filename}"

    try:
        with open(temp_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)

        cleaned = clean_audio(str(temp_path))
        stt_result = transcribe_speech(cleaned, language_mode=language_mode)
        translation = transcribe_to_english(cleaned)

        return {
            "status": "ok",
            "raw_transcript": stt_result.get("text", ""),
            "detected_language": stt_result.get("detected_language", "en"),
            "confidence": stt_result.get("confidence", 0.0),
            "confidence_stats": stt_result.get("confidence_stats", {}),
            "is_reliable": stt_result.get("is_reliable", False),
            "english_translation": translation.get("english_text", stt_result.get("text", ""))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass


# ==========================================
# STANDALONE ML MODEL ENDPOINTS
# (Sentiment/Emotion, Categorisation, Priority)
# ==========================================

# Load ML model functions via importlib (same collision-safe approach)
_cat_mod = _load_module("backend_app.categorization.model", BACKEND_APP_DIR / "categorization" / "model.py")
_sent_mod = _load_module("backend_app.sentiment_emotion.model", BACKEND_APP_DIR / "sentiment_emotion" / "model.py")
_prio_mod = _load_module("backend_app.priority.model", BACKEND_APP_DIR / "priority" / "model.py")

_predict_category = getattr(_cat_mod, "predict_category", None) if _cat_mod else None
_predict_sentiment_emotion = getattr(_sent_mod, "predict_sentiment_emotion", None) if _sent_mod else None
_predict_priority = getattr(_prio_mod, "predict_priority", None) if _prio_mod else None


class TextAnalysisRequest(BaseModel):
    text: str

class SentimentResponse(BaseModel):
    sentiment: str
    sentiment_confidence: float
    emotion: str
    emotion_confidence: float

class CategoryResponse(BaseModel):
    category: str
    sub_category: str

class PriorityRequest(BaseModel):
    sentiment: str
    emotion: str
    category: str
    sub_category: str

class PriorityResponse(BaseModel):
    priority: str
    score: float
    priority_rank: int


@app.post("/api/sentiment", response_model=SentimentResponse)
def analyse_sentiment(req: TextAnalysisRequest):
    """Run DistilBERT sentiment & emotion analysis on input text."""
    if not _predict_sentiment_emotion:
        raise HTTPException(status_code=503, detail="Sentiment model not loaded.")
    result = _predict_sentiment_emotion(req.text)
    return SentimentResponse(**result)


@app.post("/api/categorise", response_model=CategoryResponse)
def categorise_text(req: TextAnalysisRequest):
    """Run TF-IDF + SVM categorisation on input text."""
    if not _predict_category:
        raise HTTPException(status_code=503, detail="Categorisation model not loaded.")
    result = _predict_category(req.text)
    return CategoryResponse(**result)


@app.post("/api/priority", response_model=PriorityResponse)
def calculate_priority(req: PriorityRequest):
    """Calculate business priority score from sentiment + category inputs."""
    if not _predict_priority:
        raise HTTPException(status_code=503, detail="Priority model not loaded.")
    result = _predict_priority(
        sentiment=req.sentiment,
        emotion=req.emotion,
        category=req.category,
        sub_category=req.sub_category
    )
    return PriorityResponse(**result)


# ==========================================
# LANGGRAPH ORCHESTRATION ENDPOINT
# (Sentiment + Categorisation + Priority + RAG + LLM + Evaluation in one shot)
# ==========================================

class OrchestrationRequest(BaseModel):
    query: str
    user_id: str = None
    use_local_llm: bool = True
    evaluate_response: bool = True

@app.post("/api/orchestration/process")
def run_langgraph_orchestration(req: OrchestrationRequest):
    """
    Full LangGraph Pipeline:
    Categorisation → Sentiment & Emotion → Priority → Insights Routing →
    RAG Retrieval → LLM Generation → RAG Evaluation → Escalation Handover
    """
    result = orchestrator.run(
        query=req.query,
        user_id=req.user_id,
        use_local_llm=req.use_local_llm,
        evaluate_response=req.evaluate_response
    )
    return result


@app.get("/api/orchestration/topology")
def get_graph_topology():
    """Returns the LangGraph node topology and state schema."""
    return {
        "nodes": [
            "categorization_node (TF-IDF + SVM)",
            "sentiment_node (DistilBERT Multi-task)",
            "priority_node (Business Rules Engine)",
            "insights_routing_node (Escalation SLA Decision)",
            "rag_retrieval_node (Pinecone Vector Search)",
            "rag_generation_node (Gemma 3 / Gemini LLM)",
            "rag_evaluation_node (RAGAS & Hallucination Check)",
            "escalation_handover_node (Human Desk Router)"
        ],
        "state_schema": [
            "query", "user_id", "category", "sub_category",
            "sentiment", "sentiment_confidence", "emotion", "emotion_confidence",
            "priority", "priority_score", "priority_rank",
            "escalation_required", "escalated_to_human", "recommended_action",
            "retrieved_chunks", "response", "llm_source",
            "evaluation", "execution_nodes", "elapsed_time_sec"
        ]
    }


# ==========================================
# RAG PIPELINE ENDPOINTS
# (Chunk, Embed, Retrieve/VectorStore, LLM Generate, Evaluate, Full Query)
# ==========================================

from orchestration import Orchestrator
from chunking import DocumentChunker
from embeddings import EmbeddingsEngine
from retriever import TelecomRAGRetriever
from context_engineering import RerankLayer
from rag_evaluation import HallucinationEvaluator
from ragas_eval import RAGASEvaluator

# Lazy-initialised RAG singletons (heavy, loaded on first call)
_rag_orchestrator = None
_rag_retriever = None
_embeddings_engine = None
_halluc_eval = None
_ragas_eval = None
_reranker = None

def _get_rag_components():
    global _rag_orchestrator, _rag_retriever, _embeddings_engine, _halluc_eval, _ragas_eval, _reranker
    if _rag_orchestrator is None:
        _rag_orchestrator = Orchestrator(ollama_model="gemma3:latest")
        _rag_retriever = TelecomRAGRetriever()
        _embeddings_engine = EmbeddingsEngine()
        _halluc_eval = HallucinationEvaluator()
        _ragas_eval = RAGASEvaluator()
        _reranker = RerankLayer()
    return _rag_orchestrator, _rag_retriever, _embeddings_engine, _halluc_eval, _ragas_eval, _reranker


# --- Pydantic Schemas for RAG endpoints ---

class ChunkRequest(BaseModel):
    text: str
    max_tokens: int = 256
    overlap_tokens: int = 32
    min_chunk_tokens: int = 80

class EmbedRequest(BaseModel):
    texts: List[str]
    model_name: str = "all-MiniLM-L6-v2"
    normalize: bool = True

class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5
    category: str = None
    language: str = None
    sentiment: str = None
    priority: str = None

class GenerateRequest(BaseModel):
    query: str
    context_text: str
    system_prompt: str = None
    use_local: bool = True

class EvaluateRequest(BaseModel):
    query: str
    response: str
    context_texts: List[str]

class RAGQueryRequest(BaseModel):
    query: str
    strategy: str = "semantic"
    use_local: bool = True
    top_k: int = 5
    evaluate: bool = True
    category: str = None
    language: str = None
    sentiment: str = None
    priority: str = None

class RankRequest(BaseModel):
    query: str
    candidates: List[str]


# --- RAG Endpoints ---

@app.post("/api/rag/chunk")
def chunk_text(req: ChunkRequest):
    """Segment raw text into optimised token-aware chunks."""
    chunker = DocumentChunker(
        max_tokens=req.max_tokens,
        overlap_tokens=req.overlap_tokens,
        min_chunk_tokens=req.min_chunk_tokens
    )
    splits = chunker.split_text(req.text)
    chunks = [{"text": t, "token_count": chunker.count_tokens(t), "index": i} for i, t in enumerate(splits)]
    return {"chunks": chunks, "total_chunks": len(chunks)}


@app.post("/api/rag/embed")
def embed_text(req: EmbedRequest):
    """Generate normalised vector embeddings for input texts."""
    _, _, emb_engine, _, _, _ = _get_rag_components()
    import numpy as np
    if emb_engine.model_name != req.model_name:
        emb_engine.change_model(req.model_name)
    embeddings = emb_engine.encode(req.texts, normalize_embeddings=req.normalize)
    emb_list = embeddings.tolist() if isinstance(embeddings, np.ndarray) else list(embeddings)
    if len(emb_list) > 0 and not isinstance(emb_list[0], list):
        emb_list = [emb_list]
    return {"embeddings": emb_list, "model_name": req.model_name, "dimension": emb_engine.dimension}


@app.post("/api/rag/retrieve")
def retrieve_context(req: RetrieveRequest):
    """Retrieve relevant document chunks from Pinecone vector store with optional metadata filters."""
    _, retriever, _, _, _, _ = _get_rag_components()
    results = retriever.retrieve(
        query=req.query, top_k=req.top_k,
        category=req.category, language=req.language,
        sentiment=req.sentiment, priority=req.priority
    )
    items = []
    for r in results:
        chunk = r.get("chunk", {})
        items.append({
            "text": chunk.get("text") or chunk.get("raw_text") or "",
            "score": r.get("score", 0.0),
            "metadata": chunk.get("metadata", {})
        })
    return {"results": items, "count": len(items)}


@app.post("/api/rag/llm")
def generate_llm(req: GenerateRequest):
    """Generate LLM response using Gemma 3 (local) or Gemini (cloud)."""
    orch, _, _, _, _, _ = _get_rag_components()
    t0 = time.time()
    from prompt_templates import detect_language, build_system_prompt, build_user_prompt, build_full_prompt
    language = detect_language(req.query)
    sys_prompt = req.system_prompt or build_system_prompt(language)
    user_prompt = build_user_prompt(req.query, language)
    full_prompt = build_full_prompt(sys_prompt, req.context_text, user_prompt)

    response = ""
    llm_source = ""
    if req.use_local:
        if orch.ollama.is_available():
            response = orch.ollama.generate(prompt=full_prompt, system=sys_prompt, temperature=0.2, max_tokens=512)
            llm_source = f"ollama_{orch.ollama.model}"
        else:
            response = orch.gemini_client.generate_response(sys_prompt, req.query, retrieved_context=req.context_text)
            llm_source = "gemini_client_fallback"
    else:
        response = orch.gemini_client.generate_response(sys_prompt, req.query, retrieved_context=req.context_text)
        llm_source = "gemini_client"

    return {"response": response, "llm_source": llm_source, "elapsed_sec": round(time.time() - t0, 2)}


@app.post("/api/rag/evaluate")
def evaluate_response(req: EvaluateRequest):
    """Run hallucination analysis and RAGAS metrics on query/response/context."""
    _, _, _, h_eval, r_eval, _ = _get_rag_components()
    halluc = h_eval.run_full_evaluation(req.response, req.context_texts) if h_eval else None
    ragas = r_eval.evaluate_sample(req.query, req.response, req.context_texts) if r_eval else None
    return {"hallucination_eval": halluc, "ragas_eval": ragas}


@app.post("/api/rag/rank")
def rank_context(req: RankRequest):
    """Perform requirement-aware reranking on context candidates."""
    _, _, _, _, _, reranker = _get_rag_components()
    search_results = [{"chunk": {"text": t}, "score": 1.0} for t in req.candidates]
    ranked = reranker.rerank(search_results, req.query)
    items = [{"text": r.get("text", ""), "rerank_score": r.get("rerank_score") or r.get("score", 0.0)} for r in ranked]
    return {"ranked": items}


@app.post("/api/rag/query")
def full_rag_query(req: RAGQueryRequest):
    """
    Complete RAG Pipeline:
    Retrieve context → Build prompt → Generate LLM response → Evaluate (hallucination + RAGAS)
    Returns retrieval flow, prompt flow, generation flow, and evaluation results.
    """
    orch, _, emb_engine, h_eval, r_eval, _ = _get_rag_components()
    t0 = time.time()
    pipeline_out = orch.run_pipeline(
        query=req.query, strategy=req.strategy, use_local=req.use_local,
        top_k=req.top_k, category=req.category, language=req.language,
        sentiment=req.sentiment, priority=req.priority
    )
    elapsed = round(time.time() - t0, 2)
    response_text = pipeline_out["response"]
    chunks = pipeline_out["chunks"]
    chunk_texts = [c.get("chunk", {}).get("text", "") for c in chunks if c.get("chunk", {}).get("text")]

    halluc_result = None
    ragas_result = None
    if req.evaluate:
        if h_eval:
            try:
                halluc_result = h_eval.run_full_evaluation(response_text, chunk_texts)
            except Exception:
                pass
        if r_eval:
            try:
                ragas_result = r_eval.evaluate_sample(req.query, response_text, chunk_texts)
            except Exception:
                pass

    retrieval_flow = []
    for c in chunks:
        co = c.get("chunk", {})
        retrieval_flow.append({
            "text": co.get("text") or co.get("raw_text") or "",
            "score": float(c.get("score", 0.0)),
            "metadata": co.get("metadata", {})
        })

    return {
        "query": req.query,
        "strategy": req.strategy,
        "embedding_metadata": {"model_name": emb_engine.model_name, "dimension": emb_engine.dimension},
        "retrieval_flow": retrieval_flow,
        "prompt_flow": {
            "system_prompt": pipeline_out.get("system_prompt", ""),
            "context_text": pipeline_out.get("context_text", ""),
            "full_prompt": pipeline_out.get("full_prompt", "")
        },
        "generation_flow": {
            "response": response_text,
            "llm_source": pipeline_out["llm_source"],
            "elapsed_sec": elapsed
        },
        "hallucination_eval": halluc_result,
        "ragas_eval": ragas_result
    }


@app.get("/")
@app.get("/dashboard")
def read_root():
    """Serve Unified Web Dashboard on single unified port, or fallback to Swagger API docs."""
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        from fastapi.responses import FileResponse
        return FileResponse(str(index_file))
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")



@app.get("/health")
@app.get("/api/health")
def health_check():
    """System health check."""
    return {"status": "healthy", "orchestrator": "loaded", "endpoints": "all_active"}