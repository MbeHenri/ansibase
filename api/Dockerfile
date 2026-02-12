FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["sh", "-c", "pip install --upgrade ansibase && python3 manage-db.py upgrade heads && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
