FROM python:3.10.7

WORKDIR /NotificatorBot

COPY requirements.txt ./requirements.txt

RUN apt-get update && apt-get install -y sqlite3 libsqlite3-dev
RUN pip install -r requirements.txt

COPY main.py ./main.py
COPY models.py ./models.py
COPY .env ./.env

RUN mkdir -p ./storage/temp
RUN mkdir -p ./storage/backup

CMD [ "python", "models.py" ]
CMD [ "python", "main.py" ]