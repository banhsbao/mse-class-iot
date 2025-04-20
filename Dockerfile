FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directory for SQLite database
RUN mkdir -p /data && \
    chmod 777 /data

# Environment variables
ENV DATABASE=/data/iot.db
ENV PORT=5000

# Expose the port the app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"] 