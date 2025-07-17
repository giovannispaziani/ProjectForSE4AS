FROM python:3.13

WORKDIR /app

COPY . .

RUN pip install paho-mqtt

CMD ["python", "executors.py"]