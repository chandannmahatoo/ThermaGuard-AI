import hashlib
import hmac
import secrets
import time
from collections import defaultdict
from datetime import datetime,timedelta,timezone
import jwt
from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy import select
from .config import settings
from .database import User,AreaAssignment,get_db
bearer=HTTPBearer(auto_error=False)

def hash_password(password):
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.scrypt(password.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex()
def verify_password(password,stored):
    salt,digest=stored.split(':')
    return hmac.compare_digest(digest,hashlib.scrypt(password.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex())
def token(user):
    return jwt.encode({'sub':str(user.id),'exp':datetime.now(timezone.utc)+timedelta(minutes=settings.jwt_expires_minutes)},settings.jwt_secret,algorithm=settings.jwt_algorithm)
def current(auth:HTTPAuthorizationCredentials=Depends(bearer),db=Depends(get_db)):
    try:
        payload=jwt.decode(auth.credentials,settings.jwt_secret,algorithms=[settings.jwt_algorithm])
        user=db.get(User,int(payload['sub']))
        if not user or (not settings.demo_mode and user.email.endswith('@demo.thermaguard.local')): raise ValueError()
        return user
    except (AttributeError,ValueError,KeyError,jwt.PyJWTError): raise HTTPException(401,'Authentication required')

# Simple in-process login throttling (demo-scale mitigation, not enterprise IAM):
# at most 10 failed attempts per email per 5 minutes; successful logins are not counted.
_login_failures=defaultdict(list)
def throttle_login(email):
    now=time.monotonic()
    attempts=[t for t in _login_failures.get(email,[]) if now-t<300]
    _login_failures[email]=attempts
    if len(attempts)>=10: raise HTTPException(429,'Too many failed login attempts; try again later')
def register_failed_login(email):
    _login_failures[email].append(time.monotonic())
def admin(user=Depends(current)):
    if user.role!='admin': raise HTTPException(403,'Administrator required')
    return user
def inside(event,bounds):
    return bounds[0]<=event['longitude']<=bounds[2] and bounds[1]<=event['latitude']<=bounds[3]
def allowed(user,event,db):
    return user.role=='admin' or any(inside(event,a.bounds) for a in db.scalars(select(AreaAssignment).where(AreaAssignment.organization_id==user.organization_id)))
