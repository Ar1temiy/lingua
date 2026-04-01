import base64
import hashlib
import hmac
from urllib.parse import urlencode, parse_qsl
from .config import settings
from passlib.context import CryptContext
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

''''Авторизация в вк'''
def is_valid_vk_query(query_string: str) -> bool:
    query_params = dict(parse_qsl(query_string, keep_blank_values=True))
    vk_sign = query_params.pop('sign', None)
    if not vk_sign:
        return False
    vk_params = {k: v for k, v in query_params.items() if k.startswith('vk_')}

    sorted_vk_params = dict(sorted(vk_params.items()))
    encode_params = urlencode(sorted_vk_params, doseq=True)

    secret = settings.VK_APP_SECRET.encode('utf-8')
    hash_code = hmac.new(secret, encode_params.encode('utf-8'), hashlib.sha256).digest()

    calculated_sign = base64.b64encode(hash_code).decode('utf-8')
    calculated_sign = calculated_sign.replace('+', '-').replace('/', '_').rstrip('=')

    return calculated_sign == vk_sign



'''Функции для хеширования паролей'''
def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

def verify_password(original_password: str, hashed_password: str) -> bool:
    password_bytes = original_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hash_bytes)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
