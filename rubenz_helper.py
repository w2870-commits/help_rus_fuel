from http import cookies
import os
import random
import secrets
import time
from pathlib import Path

import requests

FINGERPRINT_FILE = Path(__file__).resolve().parent / "gas_cid.txt"

main_url = "https://gdebenz.ru/"
nearby_url = "https://gdebenz.ru/api/nearby"
comments_url = "https://gdebenz.ru/api/comments"
vt_url = "https://gdebenz.ru/api/vt"

putin = "huilo"

def get_fingerprint() -> str:
    if FINGERPRINT_FILE.exists():
        value = FINGERPRINT_FILE.read_text(encoding='utf-8').strip()
        if len(value) == 32 and all(c in '0123456789abcdef' for c in value):
            return value
    value = secrets.token_hex(16)
    FINGERPRINT_FILE.write_text(value, encoding='utf-8')
    return value

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'max-age=0',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Brave";v="150"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'sec-gpc': '1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
}

fuel_text_components = [
    "92", "95", "98", "100", "ДТ"
]

queue_text_components = [
    "Очереди нет",
    "Небольшая очередь",
    "Очередь ≈5–20 машин",
    "Большая очередь"
]

connector_component = "·"

def generate_fuel_text():
    count = random.randint(1, len(fuel_text_components))
    selected = sorted(random.sample(range(len(fuel_text_components)), count))
    fuel_part = ", ".join(fuel_text_components[i] for i in selected)
    return f"{fuel_part} {connector_component} {random.choice(queue_text_components)}"

def construct_json_data(osm_id: str, name: str, lat: float, lon: float, status: str, text: str,fp: str, vt: str, cvt: str) -> dict:
    return {
        'osm_id': osm_id,
        'name': name,
        'lat': lat,
        'lon': lon,
        'status': status,
        'text': text,
        'fp': fp,
        'cf': '',
        'vt': vt,
        'cvt': cvt,
    }
def random_ru_europe_coords() -> tuple[float, float]:
    lat = random.uniform(44.0, 61.0)
    lon = random.uniform(28.0, 60.0)
    return lat, lon



def determine_status(recent_comments):
    if len(recent_comments) == 0:
        return 'yes'
    for comment in recent_comments:
        if not isinstance(comment, dict):
            continue
        status = comment.get('status')
        if status not in ('yes', 'queue', 'low', 'no'):
            continue

        if comment.get('author_reliable') is True:
            return 'no' if status == 'yes' else 'yes'

        if comment.get('on_site') is True:
            return 'no' if status == 'yes' else 'yes'

    latest_status = None
    for comment in recent_comments:
        if isinstance(comment, dict):
            latest_status = comment.get('status')
            if latest_status in ('yes', 'queue', 'low', 'no'):
                break
    if latest_status == 'yes':
        return 'no'
    return 'yes'


def help_russians_find_gas():
    with requests.Session() as s:

        s.get(main_url, headers=headers, verify=False)
        cookieDict = s.cookies.get_dict()
        time.sleep(random.randint(1, 3))
        
        lat, lon = random_ru_europe_coords()
        params = {
            'lat': f'{lat:.2f}',
            'lon': f'{lon:.2f}',
            'radius_km': '20',
        }
        nearby_stations_response = s.get(nearby_url, headers=headers, cookies=cookieDict, params=params, verify=False)
        nearby_stations_response = nearby_stations_response.json()
        time.sleep(random.randint(1, 3))

        station_list = nearby_stations_response.get('stations', [])
        for station in station_list:
            if not isinstance(station, dict):
                continue
            fingerprint = get_fingerprint()

            station_id = station.get('osm_id')
            station_name = station.get('name')
            station_lat = station.get('lat')
            station_lon = station.get('lon')
            if station_id is None or station_name is None or station_lat is None or station_lon is None:
                continue

            params = {
                'lat': station_lat,
                'lon': station_lon,
                'radius_km': '20',
            }
            s.get(nearby_url, headers=headers, cookies=cookieDict, params=params, verify=False)
            cookieDict = s.cookies.get_dict()
            params = {
                'limit': '12',
                'fp': fingerprint,
            }
            time.sleep(random.randint(1, 3))
            comments_response = s.get(comments_url + f"/{station_id}", cookies=cookieDict, headers=headers)
            comments_response_content = comments_response.json()
            station_cvt = comments_response_content.get('cvt', '')

            recent_comments_response = s.get(comments_url + f"/{station_id}/recent", params=params, cookies=cookieDict, headers=headers)
            recent_comments_response_content = recent_comments_response.json()
            determined_status = determine_status(recent_comments_response_content)
            if determined_status == 'yes':
                fuel_text = generate_fuel_text()
            else:
                fuel_text = ""
            time.sleep(random.randint(1, 3))
            vt_response = s.get(vt_url, cookies=cookieDict, headers=headers)
            vt_response_content = vt_response.json()
            station_vt = vt_response_content.get('vt', '')

            cookieDict = s.cookies.get_dict()
            json_data = construct_json_data(
                osm_id=station_id,
                name=station_name,
                lat=station_lat,
                lon=station_lon,
                status=determined_status,
                text=fuel_text,
                fp=fingerprint,
                vt=station_vt,
                cvt=station_cvt)

            help_response = s.post(comments_url, json=json_data, cookies=cookieDict, headers=headers, verify=False)
            help_response_content = help_response.json()
            print("russians helped with gas station:", station_name, "at", station_lat, station_lon)
            print(help_response_content)
            time.sleep(random.randint(2, 10))
        return True
    

while putin == "huilo":
    help_russians_find_gas()
    time.sleep(random.randint(10, 60))