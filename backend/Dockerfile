FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system doiter \
    && adduser --system --ingroup doiter doiter

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .
COPY docker/entrypoint.sh /entrypoint.sh

RUN mkdir -p /data /app/staticfiles \
    && chown -R doiter:doiter /app /data /entrypoint.sh \
    && chmod 755 /entrypoint.sh

USER doiter

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
