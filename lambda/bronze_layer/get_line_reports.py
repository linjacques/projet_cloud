import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
import boto3
import time

API_URL = "https://prim.iledefrance-mobilites.fr/marketplace/v2/navitia/line_reports/line_reports"
API_KEY = "dosaOPJv3Tp3lUqyAEgnOo7wLs0SeeIb"
HEADERS = {"apikey": API_KEY, "Accept": "application/json"}

S3_BUCKET = "proj-cloud-brute"
S3_PREFIX = "trafic_metro/bronze/streaming"
s3 = boto3.client("s3")

PARIS_TZ = timezone(timedelta(hours=2))

def get_api_page(page: int):
    params = {
        "filter": "contributor==shortterm.tr_idfm",
        "count": 50,
        "start_page": page
    }
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{API_URL}?{query}", headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def parse_navitia_datetime(dt_str):
    try:
        return datetime.strptime(dt_str, "%Y%m%dT%H%M%S").replace(tzinfo=PARIS_TZ)
    except Exception:
        return None


def extract_message_text(disruption: dict) -> str:
    messages = disruption.get("messages", [])
    if not messages:
        return ""
    for m in messages:
        if "title" in m.get("channel", {}).get("types", []):
            return m.get("text", "")
    return messages[0].get("text", "")


def is_today_begin(disruption: dict) -> bool:
    today = datetime.now(PARIS_TZ).date()
    for period in disruption.get("application_periods", []):
        begin = parse_navitia_datetime(period.get("begin"))
        if begin and begin.date() == today:
            return True
    return False


def fetch_metro_disruptions_today():
    results = []
    for page in range(20):
        data = get_api_page(page)
        disruptions = data.get("disruptions", [])
        for d in disruptions:
            message_text = extract_message_text(d)
            if "métro" not in message_text.lower() and "metro" not in message_text.lower():
                continue

            if not is_today_begin(d):
                continue

            results.append(d)
        time.sleep(0.3)
    return results


def save_json_to_s3(data):
    now = datetime.now(PARIS_TZ)
    date_str = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%H%M%S")
    key = f"{S3_PREFIX}/{date_str}/metro_incidents{timestamp}.json"

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json"
    )
    return key


def main():
    print("Récupération des disruptions Métro du jour (flux court terme)...")
    disruptions = fetch_metro_disruptions_today()
    print(f"{len(disruptions)} disruptions 'Métro' trouvées pour aujourdhui")

    if not disruptions:
        print("Aucune disruption Métro avec begin = aujourdhui détectée.")

    save_json_to_s3(disruptions)
    print("Données enregistrées dans S3.")


def lambda_handler(event, context):
    try:
        main()
        return {"statusCode": 200, "body": json.dumps({"message": "Sauvegarde réussie"})}
    except Exception as e:
        print("Erreur :", e)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


