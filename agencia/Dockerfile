FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
ENV DATA_DIR=/dados
VOLUME /dados
CMD ["python", "-m", "src.main"]
