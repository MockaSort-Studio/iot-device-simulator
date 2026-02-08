FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY dist/*.whl .

RUN uv pip install --system *.whl && rm *.whl

RUN useradd -m simuser
RUN chown -R simuser:simuser /app
USER simuser

ENTRYPOINT ["iotsim"]
