import os
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, time

from db import SessionLocal, engine, Base  # type: ignore
from models import Appointment  # type: ignore

load_dotenv()

app = FastAPI(title="Samchel AI API")

# Allow local dev from Vite
app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()

# Load staff list from environment or fallback to a generic inbox
def load_staff():
  staff = []
  # Support STAFF_1_NAME/STAFF_1_EMAIL .. STAFF_5_NAME/EMAIL
  for i in range(1, 6):
    name = os.getenv(f"STAFF_{i}_NAME")
    email = os.getenv(f"STAFF_{i}_EMAIL")
    staff_id = os.getenv(f"STAFF_{i}_ID") or (name.lower().replace(" ", "_") if name else None)
    if name and email and staff_id:
      staff.append({"id": staff_id, "name": name, "email": email})
  # Fallback to a single general contact
  if not staff:
    inbox = os.getenv("TO_EMAIL") or os.getenv("SMTP_USER") or "inbox@example.com"
    staff = [{"id": "general", "name": "Samchel AI Team", "email": inbox}]
  return staff

STAFF = load_staff()


class ContactRequest(BaseModel):
  name: str
  email: EmailStr
  phone: Optional[str] = None
  subject: Optional[str] = None
  message: str


@app.get("/api/health")
def health():
  return {"ok": True}

@app.get("/api/staff")
def get_staff():
  return {"staff": [{"id": s["id"], "name": s["name"]} for s in STAFF]}

def is_business_time(dt: datetime) -> bool:
  # Monday=0..Sunday=6, business hours 9:00-17:00
  if dt.weekday() > 4:
    return False
  start = datetime.combine(dt.date(), time(9, 0))
  end = datetime.combine(dt.date(), time(17, 0))
  return start <= dt < end

def generate_slots(existing: list[datetime], days: int = 14) -> list[datetime]:
  now = datetime.now()
  slots = []
  end_date = now.date() + timedelta(days=days)
  cursor = datetime.combine(now.date(), time(9, 0))
  # start from next 30 minutes
  if cursor < now:
    minute = ((now.minute // 30) + 1) * 30
    hour = now.hour + (minute // 60)
    minute = minute % 60
    cursor = now.replace(minute=0, second=0, microsecond=0)
    cursor = cursor.replace(hour=hour, minute=minute)
  while cursor.date() < end_date:
    if is_business_time(cursor):
      if cursor not in existing and cursor > now:
        slots.append(cursor)
      cursor += timedelta(minutes=30)
    else:
      # jump to next day's 9:00
      next_day = cursor.date() + timedelta(days=1)
      cursor = datetime.combine(next_day, time(9, 0))
  return slots

class CreateAppointment(BaseModel):
  staff_id: str
  start_time: datetime
  duration_min: int = 30
  name: str
  email: EmailStr
  phone: Optional[str] = ""
  notes: Optional[str] = ""

@app.post("/api/contact")
def contact(payload: ContactRequest):
  smtp_host = os.getenv("SMTP_HOST")
  smtp_port = int(os.getenv("SMTP_PORT", "587"))
  smtp_user = os.getenv("SMTP_USER")
  smtp_pass = os.getenv("SMTP_PASS")
  to_email = os.getenv("TO_EMAIL") or smtp_user

  # If SMTP not configured, log for development
  if not smtp_host or not smtp_user or not smtp_pass:
    print("[DEV] SMTP not configured. Contact message received:")
    print(payload.model_dump())
    return {"ok": True, "info": "Message received (development mode)"}

  try:
    # Prepare email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{('[Contact] ' + payload.subject) if payload.subject else 'New Contact Form Submission'}"
    msg["From"] = f"Samchel AI Website <{smtp_user}>"
    msg["To"] = to_email

    text_body = f"""
     New enquiry from Samchel AI website:

     Name: {payload.name}
     mail: {payload.email}
     Phone: {payload.phone or '-'}
     Subject: {payload.subject or '-'}
     Message:
     {payload.message}
    """.strip()

    message_html = (payload.message or '').replace('\n', '<br/>')
    html_body = f"""
    <h2>New enquiry from Samchel AI website</h2>
    <p><strong>Name:</strong> {payload.name}</p>
    <p><strong>Email:</strong> {payload.email}</p>
    <p><strong>Phone:</strong> {payload.phone or '-'}</p>
    <p><strong>Subject:</strong> {payload.subject or '-'}</p>
    <p><strong>Message:</strong></p>
    <p>{message_html}</p>
    """.strip()

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
      if smtp_port == 587:
        server.starttls(context=context)
      server.login(smtp_user, smtp_pass)
      server.sendmail(smtp_user, [to_email], msg.as_string())

    return {"ok": True}
  except Exception:
    raise HTTPException(status_code=500, detail="Failed to send email")

@app.get("/api/availability")
def availability(
  staff_id: str = Query(...),
  days: int = Query(14, ge=1, le=60),
  db: Session = Depends(get_db),
):
  if not any(s["id"] == staff_id for s in STAFF):
    raise HTTPException(status_code=404, detail="Staff not found")
  existing = db.query(Appointment).filter(Appointment.staff_id == staff_id).all()
  existing_times = [a.start_time.replace(second=0, microsecond=0) for a in existing]
  slots = generate_slots(existing_times, days=days)
  return {"slots": [s.isoformat() for s in slots]}

def send_staff_email(staff_email: str, subject: str, text_body: str, html_body: str):
  smtp_host = os.getenv("SMTP_HOST")
  smtp_port = int(os.getenv("SMTP_PORT", "587"))
  smtp_user = os.getenv("SMTP_USER")
  smtp_pass = os.getenv("SMTP_PASS")
  if not smtp_host or not smtp_user or not smtp_pass:
    print("[DEV] SMTP not configured. Appointment email would be sent to:", staff_email)
    print(text_body)
    return
  msg = MIMEMultipart("alternative")
  msg["Subject"] = subject
  msg["From"] = f"Samchel AI Booking <{smtp_user}>"
  msg["To"] = staff_email
  msg.attach(MIMEText(text_body, "plain"))
  msg.attach(MIMEText(html_body, "html"))
  context = ssl.create_default_context()
  with smtplib.SMTP(smtp_host, smtp_port) as server:
    if smtp_port == 587:
      server.starttls(context=context)
    server.login(smtp_user, smtp_pass)
    server.sendmail(smtp_user, [staff_email], msg.as_string())

@app.post("/api/appointments")
def create_appointment(payload: CreateAppointment, db: Session = Depends(get_db)):
  staff = next((s for s in STAFF if s["id"] == payload.staff_id), None)
  if not staff:
    raise HTTPException(status_code=404, detail="Staff not found")
  start = payload.start_time.replace(second=0, microsecond=0)
  if start < datetime.now():
    raise HTTPException(status_code=400, detail="Cannot book in the past")
  conflict = (
    db.query(Appointment)
    .filter(Appointment.staff_id == payload.staff_id)
    .filter(Appointment.start_time == start)
    .first()
  )
  if conflict:
    raise HTTPException(status_code=409, detail="Slot already booked")
  appt = Appointment(
    staff_id=payload.staff_id,
    start_time=start,
    duration_min=payload.duration_min,
    name=payload.name,
    email=payload.email,
    phone=payload.phone or "",
    notes=payload.notes or "",
  )
  db.add(appt)
  db.commit()
  db.refresh(appt)
  # Email staff
  when_str = start.strftime("%A, %b %d %Y at %I:%M %p")
  text_body = f"""
New appointment booked

Staff: {staff['name']}
When: {when_str}
Duration: {payload.duration_min} minutes
Client: {payload.name} ({payload.email}, {payload.phone or '-'})
Notes:
{payload.notes or '-'}
  """.strip()
  notes_html = (payload.notes or '').replace('\n','<br/>') or '-'
  html_body = f"""
  <h2>New appointment booked</h2>
  <p><strong>Staff:</strong> {staff['name']}</p>
  <p><strong>When:</strong> {when_str}</p>
  <p><strong>Duration:</strong> {payload.duration_min} minutes</p>
  <p><strong>Client:</strong> {payload.name} ({payload.email}, {payload.phone or '-'})</p>
  <p><strong>Notes:</strong><br/>{notes_html}</p>
  """.strip()
  try:
    send_staff_email(staff["email"], "New Appointment Booking", text_body, html_body)
  except Exception:
    pass
  return {"ok": True, "appointment_id": appt.id}


