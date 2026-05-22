FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p logs safe_files lab_secrets
EXPOSE 5050
CMD ["python", "app.py"]
