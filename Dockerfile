FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATABASE_PATH=/data/kharcha.sqlite
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home kharcha && mkdir /data && chown kharcha:kharcha /data /app
COPY --chown=kharcha:kharcha . .
USER kharcha
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--preload", "--access-logfile", "-", "wsgi:app"]
