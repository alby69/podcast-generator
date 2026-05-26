FROM python:3.12-slim

# Installa dipendenze di sistema (ffmpeg per pydub)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia i requisiti e installa
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installa Playwright e il browser Firefox
RUN playwright install firefox
RUN playwright install-deps firefox

# Copia il codice sorgente
COPY . .

# Variabili d'ambiente di default
ENV OUTPUT_DIR=/app/output
ENV PORT=8000

# Esponi la porta
EXPOSE 8000

# Comando di avvio
CMD ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
