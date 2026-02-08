FROM python:3.12

ADD . /workspace

RUN pip install -e /workspace

CMD ["python", "/workspace/iotsim/main.py"]
