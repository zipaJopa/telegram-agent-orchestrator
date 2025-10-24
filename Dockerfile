FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ /app/app/
COPY scripts/ /app/scripts/

# Create data directories
RUN mkdir -p /app/data/sessions

# Run FastAPI with uvicorn
CMD ["uvicorn", "app.webhook:app", "--host", "0.0.0.0", "--port", "8000"]
