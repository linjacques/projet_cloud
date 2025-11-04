import boto3
import urllib.request
import json
import datetime
import os
import ssl
from datetime import timezone, timedelta

PARIS_TZ = timezone(timedelta(hours=2))

def lambda_handler(event, context):
    bucket_name = "proj-cloud-brute"
    api_key = "dosaOPJv3Tp3lUqyAEgnOo7wLs0SeeIb"
    headers = {"apiKey": api_key}

    urls = {
        "station_information": "https://prim.iledefrance-mobilites.fr/marketplace/velib/station_information.json",
        "station_status": "https://prim.iledefrance-mobilites.fr/marketplace/velib/station_status.json"
    }

    s3 = boto3.client("s3")
    context_ssl = ssl._create_unverified_context()

    def fetch_and_upload(name, url):
        print(f"Téléchargement depuis {url} ...")

        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, context=context_ssl) as response:
            if response.status != 200:
                raise Exception(f"Erreur HTTP {response.status} pour {url}")
            data = json.loads(response.read().decode("utf-8"))

        now_paris = datetime.datetime.now(PARIS_TZ)
        date_str = now_paris.strftime("%Y-%m-%d")
        timestamp = now_paris.strftime("%Y-%m-%d_%H-%M-%S")

        # --- Partitionnement par date ---
        s3_key = f"velib/{name}/{date_str}/{name}_{timestamp}.json"
        tmp_path = f"/tmp/{name}.json"

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        s3.upload_file(tmp_path, bucket_name, s3_key)
        os.remove(tmp_path)
        print(f"Fichier {s3_key} envoyé sur S3 avec succès ({len(data.get('data', {}).get('stations', []))} enregistrements).")

    for name, url in urls.items():
        fetch_and_upload(name, url)

    print("Collecte Vélib terminée et fichiers partitionnés par date sur S3.")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Collecte Vélib terminée et fichiers partitionnés par date dans S3."
        })
    }
