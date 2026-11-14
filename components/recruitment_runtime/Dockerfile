FROM python:3.11-slim

# Installation of environment variables for UTF-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONIOENCODING=utf-8

# Installation of systems relationships
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Installation of the Work Directorate
WORKDIR /app

# Copy Dependence Files
COPY requirements.txt .

# Installation of Python Dependences
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Creation of a directory for lairs
RUN mkdir -p logs

# Establishment of access rights
RUN chmod +x *.py

# Opening of ports
EXPOSE 8000 8001 8002 8003 8004

# The default command
CMD ["python", "gateway/main.py"]