FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CERT_LAB_DATABASE_URL=sqlite:////app/data/cert_lab.sqlite3

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY content ./content

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "cert_lab.app:app", "--host", "0.0.0.0", "--port", "8000"]
