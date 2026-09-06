FROM python:3.12-slim

WORKDIR /srv
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data
COPY evals ./evals

RUN python -m app.rag.index && python -m app.db

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import httpx;httpx.get('http://localhost:8000/health').raise_for_status()"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
