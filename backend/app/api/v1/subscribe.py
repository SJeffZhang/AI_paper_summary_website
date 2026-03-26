import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.domain import Subscriber
from app.schemas.paper import ResponseModel, SubscribeRequest, UnsubscribeRequest
from app.services import notification_service

router = APIRouter()

rate_limit_store = defaultdict(list)
rate_limit_lock = Lock()


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    one_hour_ago = now - 3600

    with rate_limit_lock:
        rate_limit_store[ip] = [timestamp for timestamp in rate_limit_store[ip] if timestamp > one_hour_ago]
        if len(rate_limit_store[ip]) >= 5:
            return False
        rate_limit_store[ip].append(now)
        return True


def enforce_write_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="请求过于频繁，请一小时后再试。")


@router.post("/subscribe", response_model=ResponseModel)
def subscribe(req: SubscribeRequest, request: Request, db: Session = Depends(get_db)):
    enforce_write_rate_limit(request)

    subscriber = db.query(Subscriber).filter(Subscriber.email == req.email).first()
    now = datetime.now(timezone.utc)
    verify_token = str(uuid.uuid4())
    unsub_token = str(uuid.uuid4())
    verify_expires_at = now + timedelta(hours=24)
    unsub_expires_at = now + timedelta(hours=24)

    if subscriber is None:
        subscriber = Subscriber(
            email=req.email,
            status=0,
            verify_token=verify_token,
            unsub_token=unsub_token,
            verify_expires_at=verify_expires_at,
            unsub_expires_at=unsub_expires_at,
        )
        db.add(subscriber)
    elif subscriber.status == 1:
        subscriber.unsub_token = unsub_token
        subscriber.unsub_expires_at = unsub_expires_at
        db.flush()
        try:
            notification_service.send_subscription_management_email(req.email, unsub_token)
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=503, detail=f"邮件发送失败，请稍后重试。{exc}") from exc
        db.commit()
        return ResponseModel(code=200, msg="该邮箱已订阅，最新管理链接已发送", data=None)
    else:
        subscriber.status = 0
        subscriber.verify_token = verify_token
        subscriber.unsub_token = unsub_token
        subscriber.verify_expires_at = verify_expires_at
        subscriber.unsub_expires_at = unsub_expires_at

    db.flush()
    try:
        notification_service.send_subscription_verification_email(req.email, verify_token)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=f"邮件发送失败，请稍后重试。{exc}") from exc
    db.commit()
    return ResponseModel(code=200, msg="邮件已发送", data=None)


@router.get("/subscribe/verify")
def verify_subscription(token: str = Query(...), db: Session = Depends(get_db)):
    subscriber = db.query(Subscriber).filter(Subscriber.verify_token == token).first()
    if subscriber is None:
        raise HTTPException(status_code=400, detail="验证链接无效")

    now = datetime.now(timezone.utc)
    if subscriber.verify_expires_at is None:
        raise HTTPException(status_code=400, detail="验证链接已失效，请重新订阅")
    if subscriber.verify_expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=400, detail="验证链接已过期，请重新订阅")

    subscriber.status = 1
    subscriber.verify_token = None
    subscriber.verify_expires_at = None
    db.commit()

    return RedirectResponse(url=f"{settings.FRONTEND_URL}/?subscribe_success=1", status_code=status.HTTP_302_FOUND)


@router.post("/unsubscribe", response_model=ResponseModel)
def unsubscribe(req: UnsubscribeRequest, request: Request, db: Session = Depends(get_db)):
    enforce_write_rate_limit(request)

    subscriber = db.query(Subscriber).filter(Subscriber.unsub_token == req.token).first()
    if subscriber is None:
        raise HTTPException(status_code=400, detail="退订链接无效，请确认链接完整性。")

    now = datetime.now(timezone.utc)
    if subscriber.unsub_expires_at is None:
        raise HTTPException(status_code=400, detail="退订链接已失效，请重新获取退订链接。")
    if subscriber.unsub_expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=400, detail="退订链接已过期，请重新获取退订链接。")

    subscriber.status = 2
    db.commit()
    return ResponseModel(code=200, msg="退订成功", data=None)
