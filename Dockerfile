FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY templates/ templates/
COPY static/ static/

# Daten (DB, Excel, Fotos) liegen im gemounteten Volume, nicht im Image
ENV DB_PATH=/data/tracker.db \
    XLSX_PATH=/data/tracker.xlsx \
    PHOTO_DIR=/data/fotos \
    TZ=Europe/Berlin \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

EXPOSE 8099

# 1 Worker: der Excel-Status liegt im Prozessspeicher; Threads reichen für eine Person
CMD ["gunicorn", "-b", "0.0.0.0:8099", "--workers", "1", "--threads", "4", "app:app"]
