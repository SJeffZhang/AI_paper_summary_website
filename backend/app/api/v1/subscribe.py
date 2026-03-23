import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from app.db.session import get_db
from app.models.domain import Subscriber
from app.schemas.paper import ResponseModel, SubscribeRequest, UnsubscribeRequest
from app.core.config import settings

import time
from collections import defaultdict
from threading import Lock

router = APIRouter()

# Simple in-memory rate limiter: {ip: [timestamps]}
# TODO: For production/multi-instance deployment, replace this with a shared store (e.g., Redis or DB) 
# to ensure the "5 requests per hour" limit is consistent across all workers/instances.
rate_limit_store = defaultdict(list)
rate_limit_lock = Lock()

def check_rate_limit(ip: str):
    """
    Check if the IP has exceeded the limit of 5 requests per hour.
    """
    now = time.time()
    one_hour_ago = now - 3600
    with rate_limit_lock:
        # Filter out old timestamps
        rate_limit_store[ip] = [t for t in rate_limit_store[ip] if t > one_hour_ago]
        if len(rate_limit_store[ip]) >= 5:
            return False
        rate_limit_store[ip].append(now)
        return True

# Pseudo-mock for email sending
def mock_send_email(email: str, verify_link: str):
    print(f"--- MOCK EMAIL ---")
    print(f"To: {email}")
    print(f"Subject: Please verify your subscription")
    print(f"Body: Click here to verify: {verify_link}")
    print(f"------------------")

@router.post("/subscribe", response_model=ResponseModel)
def subscribe(req: SubscribeRequest, request: Request, db: Session = Depends(get_db)):
    """
    Submit email for subscription (Double Opt-in)
    """
    # IP Rate Limiting: 5 requests per hour
    client_ip = request.client.host
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请一小时后再试。"
        )

    # Check if already exists
    existing = db.query(Subscriber).filter(Subscriber.email == req.email).first()
    
    verify_token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    
    if existing:
        if existing.status == 1:
            return ResponseModel(code=200, msg="该邮箱已成功订阅，无需重复操作。")
        else:
            # Update token for unverified or unsubscribed
            existing.verify_token = verify_token
            existing.token_expires_at = expires_at
            existing.status = 0 # reset to unverified
            db.commit()
    else:
        # Create new
        unsubscribe_token = str(uuid.uuid4())
        new_sub = Subscriber(
            email=req.email,
            status=0,
            verify_token=verify_token,
            unsubscribe_token=unsubscribe_token,
            token_expires_at=expires_at
        )
        db.add(new_sub)
        db.commit()

    # Generate verify link
    base_url = str(request.base_url).rstrip("/")
    verify_link = f"{base_url}/api/v1/subscribe/verify?token={verify_token}"
    
    mock_send_email(req.email, verify_link)

    return ResponseModel(code=200, msg="验证邮件已发送，请查收并确认")

@router.get("/subscribe/verify")
def verify_subscription(token: str = Query(...), db: Session = Depends(get_db)):
    """
    Verify subscription via email link
    """
    subscriber = db.query(Subscriber).filter(Subscriber.verify_token == token).first()
    
    # Using a configured frontend success page redirect
    frontend_url = settings.FRONTEND_URL
    
    if not subscriber:
        raise HTTPException(status_code=400, detail="验证链接无效")
        
    # Check if expired (assuming UTC for both)
    if subscriber.token_expires_at and subscriber.token_expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="验证链接已过期，请重新订阅")

    subscriber.status = 1
    subscriber.verify_token = None
    subscriber.token_expires_at = None
    db.commit()

    # Redirect to frontend
    return RedirectResponse(url=f"{frontend_url}/?subscribe_success=1")

@router.post("/unsubscribe", response_model=ResponseModel)
def unsubscribe(req: UnsubscribeRequest, db: Session = Depends(get_db)):
    """
    Secure unsubscribe using unique token
    """
    subscriber = db.query(Subscriber).filter(Subscriber.unsubscribe_token == req.token).first()
    
    if not subscriber:
        raise HTTPException(status_code=400, detail="退订链接无效或已过期，请确认链接完整性。")
        
    subscriber.status = 2 # unsubscribed
    db.commit()
    
    return ResponseModel(code=200, msg="退订成功")
