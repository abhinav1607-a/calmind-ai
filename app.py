import os
from datetime import datetime, timedelta
import uuid

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, session
from flask_pymongo import PyMongo
from textblob import TextBlob

load_dotenv()
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-this-development-secret")
app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb://localhost:27017/calmind")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
mongo = PyMongo(app)
moods, journals, chats = mongo.db.moods, mongo.db.journals, mongo.db.chats

def visitor_id():
    """Give each browser a private anonymous workspace without requiring an account."""
    if "visitor_id" not in session:
        session["visitor_id"] = str(uuid.uuid4())
    return session["visitor_id"]

def serialize(doc):
    if not doc:
        return None
    doc["id"] = str(doc.pop("_id"))
    for key, value in list(doc.items()):
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    return doc

@app.get("/")
def index():
    visitor_id()
    return render_template("index.html")

@app.get("/api/summary")
def summary():
    uid = visitor_id()
    since = datetime.utcnow() - timedelta(days=7)
    mood_rows = list(moods.find({"user_id": uid, "created_at": {"$gte": since}}).sort("created_at", 1))
    journal_rows = list(journals.find({"user_id": uid, "created_at": {"$gte": since}}).sort("created_at", 1))
    mood_counts = {}
    for row in mood_rows:
        mood_counts[row["mood"]] = mood_counts.get(row["mood"], 0) + 1
    scores = [r.get("score", 0) for r in mood_rows]
    avg = round(sum(scores) / len(scores), 1) if scores else 0
    return jsonify({"mood_count": len(mood_rows), "journal_count": len(journal_rows), "average_mood": avg, "mood_counts": mood_counts, "moods": [serialize(r) for r in mood_rows], "journals": [serialize(r) for r in journal_rows[-5:][::-1]]})

@app.get("/api/moods")
@login_required
def get_moods():
    rows = list(moods.find({"user_id": visitor_id()}).sort("created_at", -1).limit(30))
    return jsonify([serialize(r) for r in rows])

@app.post("/api/moods")
@login_required
def add_mood():
    data = request.get_json(silent=True) or {}
    mood = str(data.get("mood", "")).strip()
    note = str(data.get("note", "")).strip()[:1000]
    valid = {"Great": 5, "Good": 4, "Okay": 3, "Low": 2, "Anxious": 1}
    if mood not in valid:
        return jsonify({"error": "Choose a valid mood."}), 400
    result = moods.insert_one({"user_id": session["user_id"], "mood": mood, "score": valid[mood], "note": note, "created_at": datetime.utcnow()})
    return jsonify({"ok": True, "id": str(result.inserted_id)}), 201

@app.get("/api/journals")
@login_required
def get_journals():
    rows = list(journals.find({"user_id": session["user_id"]}).sort("created_at", -1).limit(30))
    return jsonify([serialize(r) for r in rows])

@app.post("/api/journals")
@login_required
def add_journal():
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()[:120]
    body = str(data.get("body", "")).strip()[:10000]
    if not body:
        return jsonify({"error": "Write a few words before saving."}), 400
    analysis = TextBlob(body).sentiment
    row = {"user_id": session["user_id"], "title": title or "Untitled reflection", "body": body, "polarity": round(float(analysis.polarity), 3), "subjectivity": round(float(analysis.subjectivity), 3), "created_at": datetime.utcnow()}
    result = journals.insert_one(row)
    return jsonify({"ok": True, "id": str(result.inserted_id), "sentiment": sentiment_label(row["polarity"])}), 201

def sentiment_label(polarity):
    if polarity > 0.15:
        return "Positive"
    if polarity < -0.15:
        return "Negative"
    return "Neutral"

@app.post("/api/chat")
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()[:4000]
    if not message:
        return jsonify({"error": "Type a message first."}), 400
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        reply = ("I'm here with you. Try taking one slow breath, then name one thing you can see, "
                 "one thing you can feel, and one small next step that would help. Add GEMINI_API_KEY "
                 "to your environment to enable AI-generated responses.")
    else:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = ("You are Calmind, a supportive mindfulness and reflection companion. "
                      "Be warm, grounded, concise, non-judgmental, and avoid diagnosing. "
                      "Offer practical coping ideas and ask at most one gentle follow-up question. "
                      "You are not a therapist or emergency service. If the user describes immediate danger "
                      "or intent to harm themselves, encourage contacting local emergency services and a trusted person. "
                      "User message: " + message)
            response = client.models.generate_content(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), contents=prompt)
            reply = response.text or "I'm listening. Could you tell me a little more about what feels most important right now?"
        except Exception:
            app.logger.exception("Gemini request failed")
            return jsonify({"error": "The AI service is temporarily unavailable. Check your Gemini API key and connection."}), 502
    chats.insert_one({"user_id": session["user_id"], "message": message, "reply": reply, "created_at": datetime.utcnow()})
    return jsonify({"reply": reply, "sentiment": sentiment_label(TextBlob(message).sentiment.polarity)})

@app.get("/api/export.csv")
@login_required
def export_csv():
    rows = list(moods.find({"user_id": session["user_id"]}, {"_id": 0, "user_id": 0}))
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["mood", "score", "note", "created_at"])
    if "created_at" in df:
        df["created_at"] = pd.to_datetime(df["created_at"]).astype(str)
    return Response(df.to_csv(index=False), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=calmind-moods.csv"})

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true", port=int(os.getenv("PORT", "5000")))
