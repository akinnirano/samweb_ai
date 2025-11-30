Environment variables (create a .env file alongside the server, same folder as main.py):

- PORT=5050
- SMTP_HOST=smtp.example.com
- SMTP_PORT=587
- SMTP_USER=your_smtp_username
- SMTP_PASS=your_smtp_password
- TO_EMAIL=your_inbox@example.com

If SMTP is not configured, the server will log contact messages to the console for development.

Run locally (FastAPI):
- python3 -m venv .venv && source .venv/bin/activate
- pip install -r requirements.txt
- uvicorn main:app --reload --port 5050


