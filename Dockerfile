FROM swaggerapi/swagger-ui:v4.18.2 AS swagger-ui
FROM python:3.10-slim-buster

ENV POETRY_VENV=/app/.venv
ENV PATH="${PATH}:${POETRY_VENV}/bin"
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -qq update \
    && apt-get -qq install --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==1.4.0 \
    && poetry config virtualenvs.in-project true

WORKDIR /app

COPY . /app
COPY --from=swagger-ui /usr/share/nginx/html/swagger-ui.css swagger-ui-assets/swagger-ui.css
COPY --from=swagger-ui /usr/share/nginx/html/swagger-ui-bundle.js swagger-ui-assets/swagger-ui-bundle.js

RUN poetry install

ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:9000", "--workers", "1", "--timeout", "0", "app.webservice:app", "-k", "uvicorn.workers.UvicornWorker"]

