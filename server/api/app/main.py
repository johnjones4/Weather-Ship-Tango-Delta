from flask import Flask, request, jsonify
import psycopg2
import app.consts as consts
from datetime import datetime, timedelta
from threading import Lock
import time

APP = Flask(__name__)
CONN = psycopg2.connect(database=consts.POSTGRES_DB, user=consts.POSTGRES_USER, password=consts.POSTGRES_PASSWORD, host=consts.POSTGRES_HOST, port=consts.POSTGRES_PORT)
CUR = CONN.cursor()
DB_LOCK = Lock()

def parse_row(row):
    return dict(
        timestamp=int(datetime.timestamp(row[0])),
        avg_wind_speed=row[1],
        min_wind_speed=row[2],
        max_wind_speed=row[3],
        temperature=row[4],
        gas=row[5],
        relative_humidity=row[6],
        pressure=row[7]
    )


def average_weather(series):
    totals = {}
    for record in series:
        for key in record:
            if key != "timestamp":
                if key not in totals:
                    totals[key] = 0.0
                totals[key] += record[key]
    averages = {}
    for key in totals:
        averages[key] = totals[key] / float(len(series))
    return averages


def get_data_in_range(start: datetime, end: datetime):
    with DB_LOCK:
        CUR.execute("SELECT timestamp, avg_wind_speed, min_wind_speed, max_wind_speed, temperature, gas, relative_humidity, pressure FROM weather WHERE timestamp >= %s AND timestamp <= %s", (start, end))
        return [parse_row(row) for row in CUR]


def insert_data(data):
    with DB_LOCK:
        print(data)
        CUR.execute("INSERT INTO weather (timestamp, avg_wind_speed, min_wind_speed, max_wind_speed, temperature, gas, relative_humidity, pressure) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (
            datetime.fromtimestamp(data["timestamp"]),
            data["avg_wind_speed"],
            data["min_wind_speed"],
            data["max_wind_speed"],
            data["temperature"],
            data["gas"],
            data["relative_humidity"],
            data["pressure"]
        ))
        CONN.commit()


@APP.route("/api")
def get_status():
    return jsonify({"status": "ok"})


@APP.route("/api/weather/series")
def get_series():
    if "start" not in request.args or "end" not in request.args:
        raise Exception("start and end parameters required")
    start = datetime.fromtimestamp(int(request.args.get("start")))
    end = datetime.fromtimestamp(int(request.args.get("end")))
    weather = get_data_in_range(start, end)
    return jsonify(weather)


@APP.route("/api/weather/average")
def get_average():
    if "range" not in request.args:
        raise Exception("range parameter required")
    drange = timedelta(minutes=int(request.args.get("range")))
    now = datetime.utcnow()
    start1 = now - drange
    end1 = now
    start2 = now - (drange * 2)
    end2 = now - drange
    current_segment = average_weather(get_data_in_range(start1, end1))
    comparison_segment = average_weather(get_data_in_range(start2, end2))
    return_data = dict()
    for key in current_segment:
        return_data[key] = dict(
            current_value=current_segment[key],
            previous_value=comparison_segment[key]
        )
    return jsonify(return_data)


@APP.route("/api/weather", methods=["POST"])
def post_data():
    if not request.json:
        raise Exception("no json body")
    weather = request.json
    if not weather["timestamp"]:
        weather["timestamp"] = time.time()
    insert_data(weather)
    return jsonify(weather)
