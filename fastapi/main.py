import logging
import secrets
import time
from typing import Any

import numpy as np
import onnxruntime as ort

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from pydantic import BaseModel,Field, conint, confloat

from fastapi.main_gpt import security

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ml-serving")

app = FastAPI(
    title="ONNX API",
    description="REST API для ONNX модели диабета",
    version="1.0.0",
)


DEMO_USER = "demo_user"
DEMO_PASS = "demo_pass"


def verify_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    correct_username = secrets.compare_digest(credentials.username, DEMO_USER)
    correct_pass = secrets.compare_digest(credentials.password, DEMO_PASS)

    if not (correct_username and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oh shit! I'm sorry! Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


class PatientFeatures(BaseModel):
    pregnancies: conint(ge=0, le=30) = Field(..., description="Количество беременностей", alias="Pregnancies"),
    glucose: conint(ge=0, le=500) = Field(..., description="Уровень глюкозы", alias="Glucose"),
    bmi: confloat(ge=0, le=100) = Field(..., description="Индекс массы тела", alias="BMI"),
    Age: conint(ge=0, le=120) = Field(..., description="Возраст", alias="Age")


session: ort.InferenceSession | None = None
input_name: str | None = None


@app.on_event("startup")
def load_model() -> None:
    global session, input_name

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


def extract_probability(raw_output: Any) -> float:
    arr = np.array(raw_output)
    flat = arr.reshape(-1)

    if flat.size == 1:
        return float(flat[0])

    if flat.size >= 2:

        return float(flat[1])


    return float(arr.item())


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


@app.get("/")
def root():
    return {"message": "Hello! This is an ONNX ML inference service."}


@app.post("/predict")
def predict(payload: PatientFeatures, username: str = Depends(verify_user)):
    if session is None or input_name is None:
        raise HTTPException(status_code=500, detail="Oh shit! I'm sorry! Model is not loaded")

    x = np.array(
        [[payload.Pregnancies, payload.Glucose, payload.BMI, payload.Age]],
        dtype=np.float32,
    )
    try:
        outputs = session.run(None, {input_name: x})
    except Exception as e:
        logger.exception("Inference failed for user=%s", username)
        raise HTTPException(status_code=500, detail=f"Inference error: {e}")

    prob = extract_probability(outputs[0])
    prediction = 1 if prob > 0.5 else 0

    logger.info("Predict by user=%s -> prob=%.6f pred=%d", username, prob, prediction)

    return {"prediction": prediction}
