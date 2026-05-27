FROM python:3.12-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install firefox
RUN playwright install-deps firefox

COPY podcast_generator/ podcast_generator/
COPY main.py .
COPY .env.example .env

ENV OUTPUT_DIR=/app/output
ENV WEB_PORT=8000
ENV WEB_HOST=0.0.0.0

EXPOSE 8000

CMD ["uvicorn", "podcast_generator.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
