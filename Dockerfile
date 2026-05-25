# Gunakan image Python resmi yang stabil dan ringan
FROM python:3.11-slim

# Atur environment variable agar Python bekerja optimal di dalam container
# PYTHONDONTWRITEBYTECODE: Mencegah Python menulis file .pyc ke dalam disk
# PYTHONUNBUFFERED: Memastikan log output Python langsung muncul di terminal secara real-time
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Tentukan direktori kerja utama di dalam container
WORKDIR /app

# Install dependensi sistem yang umum dibutuhkan (compiler dan tools esensial)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy berkas requirements.txt terlebih dahulu untuk memanfaatkan caching Docker
COPY requirements.txt /app/

# Install seluruh library Python yang dibutuhkan proyek SIMPADI
RUN pip install --no-cache-dir -r requirements.txt

# Membuat folder db dan media di dalam container terlebih dahulu
RUN mkdir -p /app/db /app/media
# ---------------------------

# Copy seluruh source code proyek SIMPADI dari komputer Anda ke dalam container
COPY . /app/

# Informasikan bahwa container ini akan menggunakan port 8000 secara internal
EXPOSE 8000

# Perintah default untuk menjalankan Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]