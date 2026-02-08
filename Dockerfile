FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/${{ github.repository }}"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY dist/*.whl .

RUN uv pip install --system *.whl && rm *.whl

RUN useradd -m simuser
USER simuser

ENTRYPOINT ["iotsim"]
