FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run with uvicorn, binding to 0.0.0.0 for LAN access
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
