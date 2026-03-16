FROM python:3.10-slim

# Configuraciones para que Python corra más rapido y limpio en Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Archivo de requerimientos
COPY requirements.txt .

# Dependencias
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia de todo el codigo backend y las carpetas de modelos/videos
COPY . .

# puerto de FastAPI
EXPOSE 8000

# Arranque de servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]