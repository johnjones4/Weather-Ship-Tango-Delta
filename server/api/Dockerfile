FROM python:3.7
WORKDIR /code
ENV FLASK_APP=main.py:APP
ENV FLASK_RUN_HOST=0.0.0.0
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . . 
EXPOSE 5000
VOLUME /sock
CMD ["uwsgi", "--ini", "uwsgi.ini"]
