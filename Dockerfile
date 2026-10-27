FROM python:3.13-slim
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock && useradd --create-home studytrace
COPY . .
RUN mkdir -p /app/local-data && chown -R studytrace:studytrace /app
USER studytrace
EXPOSE 8766
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8766", "--no-access-log"]
