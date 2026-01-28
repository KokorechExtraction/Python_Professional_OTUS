import logging
import os
import uuid

import time
from typing import Any

import numpy as np
import onnxruntime as ort
import jwt
import bcrypt

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pydantic import BaseModel, ConfigDict, Field, conint, confloat

from fastapi import security
from starlette.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ml-serving")


@dataclass(frozen=True)
class Settings:
    jwt_secret: str = os.getenv("JWT_SECRET", "change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_ttl_minutes: int = int(os.getenv("JWT_TTL_MINUTES", "30"))
    default_role: str = os.getenv("DEFAULT_ROLE", "user")

    admin_username: str | None = os.getenv("ADMIN_USERNAME")
    admin_password: str | None = os.getenv("ADMIN_PASSWORD")
    service_version: str = os.getenv("SERVICE_VERSION", "1.0.0")


settings = Settings()

if settings.jwt_secret == "change-me":
    logger.warning("Oh shit! I'm sorry! JWT_SECRET is not set. Using a default value is unsafe for production.")

ROLE_RANK = {"user": 1, "admin": 2}


@dataclass
class User:
    id: str
    username: str
    password_hash: str
    role: str


users_by_id: dict[str, User] = {}
users_by_username: dict[str, User] = {}


def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def _create_user(username: str, password: str, role: str) -> User:
    user = User(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=_hash_password(password),
        role=role,
    )
    users_by_id[user.id] = user
    users_by_id[user.username] = user
    return user


def _ensure_role_known(role: str) -> None:
    if role not in ROLE_RANK:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Oh shit! I'm sorry! Unknown role configured: {role}"
        )



def create_access_token(*, user: User) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.jwt_ttl_minutes)

    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.jwt_ttl_minutes * 60,
    }


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "role"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")



app = FastAPI(
    title="ONNX API",
    description="REST API для ONNX модели диабета (JWT + RBAC)",
    version=settings.service_version,
)


bearer_scheme = HTTPBearer(auto_error=False)

started_at = time.time()
total_requests = 0
predict_requests = 0

session: ort.InferenceSession | None = None
input_name: str | None = None


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc = RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


@app.on_event("start_up")
def start_up() -> None:
    global session, input_name

    _ensure_role_known(settings.default_role)

    if settings.admin_username and settings.admin_password:
        if settings.admin_username not in users_by_username:
            _create_user(settings.admin_username, settings.admin_password, "admin")
            logger.info("Oh shit! I'm sorry! Seeded admin user from env: %s", settings.admin_username)

    model_path = "diabetes_model.onnx"
    session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

    inputs = session.get_inputs()
    if not inputs:
        raise RuntimeError("Oh shit! I'm sorry! ONNX model has no inputs!")

    input_name = inputs[0].name
    logger.info("Model loaded from: %s", model_path)
    logger.info("Model input name: %s", input_name)
    logger.info("Model input shape: %s", inputs[0].shape)
    logger.info("Model input type: %s", inputs[0].type)
    logger.info("Model outputs: %s", [o.name for o in session.get_outputs()])


@app.middleware("http")
async def log_request(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    logger.info(
        "%s %s -> %s (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, examples=["alice"])
    password: str = Field(..., min_length=8, max_length=128, examples=["S3cureP@ssw0rd"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, examples=["alice"])
    password: str = Field(..., min_length=8, max_length=128, examples=["S3cureP@ssw0rd"])


class UserProfile(BaseModel):
    id: str
    username: str
    role: str


class PatientFeatures(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pregnancies: conint(ge=0, le=30) = Field(..., description="Количество беременностей", alias="Pregnancies"),
    glucose: conint(ge=0, le=500) = Field(..., description="Уровень глюкозы", alias="Glucose"),
    bmi: confloat(ge=0, le=100) = Field(..., description="Индекс массы тела", alias="BMI"),
    Age: conint(ge=0, le=120) = Field(..., description="Возраст", alias="Age")


class PredictResponse(BaseModel):
    prediction: int
    probability: float
    threshold: float = 0.5


def get_current_user(
        creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    payload = decode_access_token(creds.credentials)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = users_by_id.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


def require_role(min_role: str):
    _ensure_role_known(min_role)

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if ROLE_RANK.get(user.role, 0) < ROLE_RANK[min_role]:
            logger.warning("Access denied: user=%s role=%s need=%s", user.username, user.role, min_role)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Oh shit! I'm sorry! Forbidden")
        return user
    return _dependency


@app.get("/")
def root():
    return {"message": "Hello! This is an ONNX ML inference service."}


@app.post("/auth/register", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    username = payload.username.strip()

    if username in users_by_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    role = settings.default_role
    _ensure_role_known(role)


    user = _create_user(username, payload.password, role)
    logger.info("User registered: %s role=%s", user.username, user.role)
    return UserProfile(id=user.id, username=user.username, role=user.role)


@app.post("/auth/login")
def login(payload: LoginRequest):
    username = payload.username.strip()
    user = users_by_username.get(username)

    if not user or not _verify_password(payload.password, user.password_hash):
        logger.warning("Oh shit! I'm sorry! Login failed for username=%s", username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Oh shit! I'm sorry! Invalid credentials")

    token_data = create_access_token(user=user)
    logger.info("Login success: user=%s role=%s", user.username, user.role)
    return token_data


@app.get("/me", response_model=UserProfile)
def me(user: User = Depends(get_current_user)):
    return UserProfile(id=user.id, username=user.username, role=user.role)


def extract_probability(raw_output: Any) -> float:
    arr = np.array(raw_output)
    flat = arr.reshape(-1)

    if flat.size == 1:
        return float(flat[0])

    if flat.size >= 2:

        return float(flat[1])

    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Oh shit! I'm sorry!Unexpected model output")


@app.post("/predict", response_model=PredictResponse)
def predict(
        features: PatientFeatures,
        user: User = Depends(require_role("user")),
):

    global predict_requests

    if session is None or input_name is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Model is not loaded")

    x = np.array(
        [[features.pregnancies, features.glucose, features.bmi, features.age]],
        dtype=np.float32,
    )
    outputs = session.run(None, {input_name: x})
    if not outputs:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Model returned no outputs")

    prob = extract_probability(outputs[0])
    pred = 1 if prob > 0.5 else 0

    predict_requests += 1
    logger.info("Predict by user=%s -> prob=%.6f pred=%d", user.username, prob, pred)

    return PredictResponse(prediction=pred, probability=prob)


@app.get("/admin/metrics")
def admin_metrics(admin: User = Depends(require_role("admin"))):
    """Пример админского эндпоинта: только для роли admin."""
    uptime_s = time.time() - started_at
    return {
        "uptime_s": round(uptime_s, 3),
        "total_requests": total_requests,
        "predict_requests": predict_requests,
        "version": settings.service_version,
        "admin": admin.username,
    }
