FROM python:3.11-alpine3.17

ADD server/ /app
WORKDIR /app

RUN python3 -m pip install -r requirements.txt
CMD ["python3", "main.py"]
