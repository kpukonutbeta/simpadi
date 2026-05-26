# Gunakan image Python resmi yang stabil dan ringan
FROM python:3.11-slim

# Atur environment variable agar Python bekerja optimal di dalam container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Tentukan direktori kerja utama di dalam container
WORKDIR /app

# Install dependensi sistem yang esensial
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy berkas requirements.txt terlebih dahulu
COPY requirements.txt /app/

# Install seluruh library Python yang dibutuhkan proyek SIMPADI
RUN pip install --no-cache-dir -r requirements.txt

# Membuat folder db dan media kosong sebagai placeholder sebelum di-mount volume
RUN mkdir -p /app/db /app/media

# Copy seluruh source code proyek SIMPADI dari komputer ke dalam container
COPY . /app/

# Menggunakan port 8000 secara internal
EXPOSE 8000

# Perintah default hanya untuk menjalankan server Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]