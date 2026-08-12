FROM python:3.9-slim

WORKDIR /app

# Copy requirements file first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy Intern files into container
COPY . .

# Expose port
EXPOSE 8000

# Run FastAPI using uvicorn (inside WORKDIR /app, main.py is root module)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
