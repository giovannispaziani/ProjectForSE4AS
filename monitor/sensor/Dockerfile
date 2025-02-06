FROM python:3.9

WORKDIR /app

COPY . .

RUN pip install paho-mqtt

CMD ["python", "sensors.py"]