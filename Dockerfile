FROM python:3.11-slim

# libs do sistema p/ áudio
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libopus0 libsodium23 build-essential libffi-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
