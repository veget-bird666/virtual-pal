# ============================
# Stage 1: Builder
# ============================
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================
# Stage 2: Runtime
# ============================
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY ./app /app/app

ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
