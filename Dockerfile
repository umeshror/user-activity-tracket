FROM python:3.7-alpine

RUN mkdir -p /se
WORKDIR /se

ENV FLASK_APP run.py
ENV FLASK_RUN_HOST 0.0.0.0

RUN apk add --no-cache gcc musl-dev linux-headers

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .
RUN flask db upgrade

CMD ["python", "run.py"]
EXPOSE 5000
