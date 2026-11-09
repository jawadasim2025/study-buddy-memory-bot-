# Study Buddy: A Long-Term Memory AI Agent

A command-line study buddy that remembers users across separate sessions. It stores raw messages and extracted facts in MongoDB, uses the Gemini API to pull out facts worth remembering, and adds the user's memories to every prompt.

## Features

- Two MongoDB collections: `conversations` (raw messages) and `memories` (extracted facts per user)
- LLM-based fact extraction (preferences, goals, personal details)
- Memory retrieval before every reply
- Duplicate avoidance and updating of changed facts
- `/memories` to view stored memories, `/forget <key>` or `/forget all` to delete them
- Secrets kept in environment variables, never in code

## Tech stack

Python, pymongo, python-dotenv, Google Gemini API (google-genai), MongoDB Atlas (free tier)

## Setup

1. Clone the repo and open the folder.
2. Install packages:

       pip install -r requirements.txt

3. Create a free MongoDB Atlas cluster and a database user, then copy the connection string.
4. Get a free Gemini API key from Google AI Studio.
5. Create a file named `.env` in the project folder:

       MONGODB_URI=your_connection_string
       GEMINI_API_KEY=your_gemini_key

   The `.env` file is listed in `.gitignore` and must never be committed.

## Run

    python main.py

Enter a name when asked. Use the same name every session so the bot finds your memories.

## Commands

| Command | What it does |
| --- | --- |
| /memories | Shows everything the bot remembers about you |
| /forget <key> | Deletes one memory, for example /forget diet |
| /forget all | Deletes all your memories |
| /quit | Ends the session |

## How it works

1. **Store:** every user and assistant message is saved to `conversations` with a session id and timestamp.
2. **Extract:** after each user message, Gemini returns a JSON list of key-value facts worth remembering.
3. **Manage:** a new fact is inserted, an identical fact is ignored, and a fact with the same key but a new value updates the old one.
4. **Retrieve:** before each reply, the user's memories are loaded from MongoDB and added to the prompt.

## Demo

Screenshots of three separate sessions showing the bot remembering a fact are in the `screenshots` folder.