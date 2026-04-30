import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
import uvicorn

app = FastAPI()

SIGNUPS_FILE = Path("signups.json")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
TO_EMAIL = "aarav@haptal.ai"
FROM_EMAIL = "signups@haptal.ai"


def load_signups():
    if SIGNUPS_FILE.exists():
        return json.loads(SIGNUPS_FILE.read_text())
    return []


def save_signup(email: str):
    signups = load_signups()
    signups.append({"email": email, "time": datetime.now(timezone.utc).isoformat()})
    SIGNUPS_FILE.write_text(json.dumps(signups, indent=2))


async def send_email(email: str):
    if not RESEND_API_KEY:
        print(f"[SIGNUP] {email} — no RESEND_API_KEY set, skipping email")
        return
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
            json={
                "from": FROM_EMAIL,
                "to": TO_EMAIL,
                "subject": f"New Haptal signup: {email}",
                "text": f"New early access signup\n\nEmail: {email}\nTime: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\nTotal signups: {len(load_signups())}"
            }
        )


@app.post("/signup")
async def signup(request: Request):
    body = await request.json()
    email = body.get("email", "").strip()
    if not email or "@" not in email:
        return JSONResponse({"error": "invalid email"}, status_code=400)
    save_signup(email)
    await send_email(email)
    return JSONResponse({"ok": True})


@app.get("/")
async def root():
    return FileResponse("index.html")


app.mount("/", StaticFiles(directory="."), name="static")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
