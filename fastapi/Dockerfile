FROM python:3.11-slim

WORKDIR /app

# onnxruntime на slim иногда требует libgomp1
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# код приложения и модель
COPY app ./app
COPY diabetes_model.onnx ./diabetes_model.onnx

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
