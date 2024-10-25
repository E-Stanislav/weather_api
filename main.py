import json
import os
from datetime import datetime, timedelta

import redis
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

app = Flask(__name__)
limiter = Limiter(key_func=get_remote_address, app=app)

# Подключение к Redis
cache = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6379)))
api_key = os.getenv('API_KEY')
base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

def get_weather_data(city_name):
    n_date = datetime.now().date() + timedelta(days=1)
    response = requests.get(f"{base_url}/{city_name}/{n_date}", params={"key": api_key, "include": "current"})
    return response.json() if response.status_code == 200 else None

@app.route('/get_data', methods=['GET'])
@limiter.limit("5 per minute")  # Ограничение запросов для `/get_data`
def get_data():
    data = cache.get('data')
    if data:
        return jsonify({"data": data.decode('utf-8'), "source": "cache"})
    data = "Hello, world!"
    cache.setex('data', 60, data)
    return jsonify({"data": data, "source": "api"})

@app.route('/city/<city_name>', methods=['GET'])
@limiter.limit("10 per minute")  # Ограничение запросов для `/city/<city_name>`
def get_city_weather(city_name):
    cached_data = cache.get(f'data_{city_name}')
    if cached_data:
        return jsonify({"city": city_name, "source": "cache", "data": json.loads(cached_data)})
    
    data = get_weather_data(city_name)
    if data:
        cache.setex(f'data_{city_name}', 60, json.dumps(data))
        return jsonify({"city": city_name, "source": "api", "data": data,})
    return jsonify({"error": "City data not found"}), 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
