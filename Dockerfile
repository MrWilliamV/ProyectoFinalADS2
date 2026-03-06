FROM python:3.13.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    \
    default-mysql-client \
    default-libmysqlclient-dev\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt
COPY . /app/

