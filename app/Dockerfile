FROM python:3.12-alpine

# shown in the page footer; 1.1 is built with --build-arg APP_VERSION=1.1
ARG APP_VERSION=1.0
ENV APP_VERSION=${APP_VERSION} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# run as a normal user, not root
RUN adduser -D -u 10001 appuser
USER 10001

EXPOSE 8080
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
