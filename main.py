import os
import json
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient
from google import genai
from google.genai import types

load_dotenv()

MONGODB_URI = os.environ["MONGODB_URI"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-3.8-flash"

db_client = MongoClient(MONGODB_URI)
db = db_client["study_buddy"]
conversations = db["conversations"]
memories = db["memories"]

ai = genai.Client(api_key=GEMINI_API_KEY)


def now():
    return datetime.now(timezone.utc)


def ask_gemini(prompt, as_json=False):
    config = None
    if as_json:
        config = types.GenerateContentConfig(response_mime_type="application/json")
    response = ai.models.generate_content(model=MODEL, contents=prompt, config=config)
    return response.text


# ---------- STORE ----------
def save_message(user_id, session_id, role, text):
    conversations.insert_one({
        "user_id": user_id,
        "session_id": session_id,
        "role": role,
        "text": text,
        "timestamp": now(),
    })


# ---------- RETRIEVE ----------
def get_memories(user_id):
    return list(memories.find({"user_id": user_id}).sort("updated_at", 1))


def memories_as_text(user_id):
    items = get_memories(user_id)
    if not items:
        return "No memories yet."
    return "\n".join(f"- {m['key']}: {m['value']}" for m in items)


# ---------- EXTRACT + MANAGE ----------
def extract_facts(user_message):
    prompt = (
        "Extract facts worth remembering about the user from the message below. "
        "Only include lasting facts: preferences, goals, personal details, "
        "subjects they study, exam dates, how they like answers. "
        "Ignore small talk and questions. "
        'Return a JSON list like [{"key": "diet", "value": "vegetarian"}]. '
        "Use short, lowercase, consistent keys such as name, diet, "
        "answer_style, subject, goal, exam_date. "
        "If there is nothing worth remembering, return [].\n\n"
        f"Message: {user_message}"
    )
    try:
        facts = json.loads(ask_gemini(prompt, as_json=True))
        return facts if isinstance(facts, list) else []
    except Exception:
        return []


def save_facts(user_id, facts):
    for fact in facts:
        key = str(fact.get("key", "")).strip().lower()
        value = str(fact.get("value", "")).strip()
        if not key or not value:
            continue
        existing = memories.find_one({"user_id": user_id, "key": key})
        if existing is None:
            memories.insert_one({
                "user_id": user_id,
                "key": key,
                "value": value,
                "created_at": now(),
                "updated_at": now(),
            })
            print(f"  [memory saved] {key}: {value}")
        elif existing["value"].lower() == value.lower():
            pass  # duplicate, ignore
        else:
            memories.update_one(
                {"_id": existing["_id"]},
                {"$set": {"value": value, "updated_at": now()}},
            )
            print(f"  [memory updated] {key}: {existing['value']} -> {value}")


# ---------- COMMANDS ----------
def show_memories(user_id):
    items = get_memories(user_id)
    if not items:
        print("I don't remember anything about you yet.")
        return
    print("Here is what I remember about you:")
    for i, m in enumerate(items, 1):
        print(f"  {i}. {m['key']}: {m['value']}")


def forget(user_id, arg):
    if arg.strip().lower() == "all":
        result = memories.delete_many({"user_id": user_id})
        print(f"Deleted {result.deleted_count} memories.")
        return
    if not arg.strip():
        print("Use /forget <key> (for example /forget diet) or /forget all")
        return
    result = memories.delete_many({"user_id": user_id, "key": arg.strip().lower()})
    if result.deleted_count:
        print(f"Forgot '{arg.strip()}'.")
    else:
        print(f"I had no memory called '{arg.strip()}'. Try /memories to see the keys.")


# ---------- CHAT ----------
def recent_history(user_id, session_id, limit=10):
    msgs = list(conversations.find(
        {"user_id": user_id, "session_id": session_id}
    ).sort("timestamp", -1).limit(limit))
    msgs.reverse()
    return "\n".join(f"{m['role']}: {m['text']}" for m in msgs)


def reply(user_id, session_id, user_message):
    prompt = (
        "You are a friendly study buddy. Help the user learn.\n"
        "Here is what you remember about this user from earlier sessions. "
        "Always apply these (for example answer style and diet):\n"
        f"{memories_as_text(user_id)}\n\n"
        "Conversation so far:\n"
        f"{recent_history(user_id, session_id)}\n\n"
        f"user: {user_message}\nassistant:"
    )
    return ask_gemini(prompt)


def main():
    print("Study Buddy (type /memories, /forget <key|all>, or /quit)")
    user_id = input("Your name: ").strip().lower()
    session_id = now().strftime("%Y%m%d-%H%M%S")

    known = get_memories(user_id)
    if known:
        print(f"Welcome back, {user_id}! I remember {len(known)} things about you.")
    else:
        print(f"Nice to meet you, {user_id}!")

    while True:
        user_message = input("\nYou: ").strip()
        if not user_message:
            continue
        if user_message == "/quit":
            print("Bye! I will remember you next time.")
            break
        if user_message == "/memories":
            show_memories(user_id)
            continue
        if user_message.startswith("/forget"):
            forget(user_id, user_message[len("/forget"):])
            continue

        save_message(user_id, session_id, "user", user_message)
        save_facts(user_id, extract_facts(user_message))
        answer = reply(user_id, session_id, user_message)
        save_message(user_id, session_id, "assistant", answer)
        print(f"\nBuddy: {answer}")


if __name__ == "__main__":
    main()