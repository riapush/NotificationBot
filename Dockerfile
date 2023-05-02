FROM python:3.10.7

WORKDIR /NotificatorBot

COPY requirements.txt ./requirements.txt

RUN pip install -r requirements.txt

COPY main.py ./main.py
COPY models.py ./models.py
COPY .env ./.env

RUN mkdir -p ./storage/temp
RUN mkdir -p ./storage/backup

CMD [ "python", "main.py" ]