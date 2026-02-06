ARG UV_VERSION=latest

FROM ghcr.io/astral-sh/uv:$UV_VERSION AS uv
FROM mcr.microsoft.com/vscode/devcontainers/base:debian

ENV PYTHONDONTWRITEBYTECODE=True \
    PYTHONUNBUFFERED=True \
    UV_LINK_MODE=copy

# hadolint ignore=DL3008
RUN sudo apt-get update
RUN sudo apt-get install --no-install-recommends --assume-yes \
    libgl1 \
    libglib2.0-0 \
    libx11-dev \
    libosmesa6-dev \
    x11-apps \
    git-lfs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/vscode
USER vscode

RUN mkdir -p .ssh && chmod 700 .ssh

RUN ssh-keyscan -t ecdsa github.com >> .ssh/known_hosts

COPY --from=uv --chown=vscode: /uv /uvx /bin/

RUN git lfs install



