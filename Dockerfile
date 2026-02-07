FROM python:3.12

ADD . /workspace

RUN pip install -e /workspace
RUN python /workspace/iotsim/config/generate_py_parameter.py

CMD ["python", "/workspace/iotsim/src/app.py"]
