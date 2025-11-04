import boto3
import csv
import io
import os
import time
from datetime import datetime, timezone, timedelta

s3_client = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

S3_BUCKET = "proj-cloud-argent"
S3_PREFIX = "evenements_ratp_velib/"


def get_latest_csv_key(bucket, prefix):
    """Retourne le dernier CSV (le plus récent) dans tout le dossier S3 donné"""
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if "Contents" not in response:
        raise FileNotFoundError(f"Aucun fichier trouvé dans {prefix}")
    csv_files = [obj for obj in response["Contents"] if obj["Key"].endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"Aucun fichier CSV trouvé dans {prefix}")
    latest_file = max(csv_files, key=lambda x: x["LastModified"])["Key"]
    print(f"Dernier CSV trouvé : {latest_file}")
    return latest_file


def parse_csv_from_s3(bucket: str, key: str):
    """Charge et parse un CSV depuis S3 (gestion BOM + nettoyage)"""
    print(f"Lecture du fichier CSV depuis s3://{bucket}/{key}")
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read().decode("utf-8-sig")

    reader = csv.DictReader(io.StringIO(data))
    rows = [
        {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        for r in reader
    ]
    print(f"{len(rows)} lignes chargées et nettoyées.")
    return rows


def clear_table(table_name: str):
    """Vide une table DynamoDB sans la supprimer"""
    table = dynamodb.Table(table_name)
    print(f"Vidage de la table '{table_name}'...")
    deleted = 0
    scan_kwargs = {
        "ProjectionExpression": ", ".join(
            [k["AttributeName"] for k in table.key_schema]
        )
    }

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        if not items:
            break

        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key=item)
                deleted += 1

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    print(f"Table '{table_name}' vidée ({deleted} éléments supprimés).")


def create_table_if_not_exists(name, key_schema, attr_defs):
    """Crée la table DynamoDB si elle n'existe pas"""
    existing_tables = [t.name for t in dynamodb.tables.all()]
    if name in existing_tables:
        print(f"Table '{name}' déjà existante.")
        return dynamodb.Table(name)

    print(f"Création de la table '{name}'...")
    table = dynamodb.create_table(
        TableName=name,
        KeySchema=key_schema,
        AttributeDefinitions=attr_defs,
        BillingMode="PAY_PER_REQUEST"
    )
    table.wait_until_exists()
    print(f"Table '{name}' créée avec succès.")
    return table


def insert_items(table_name, items):
    """Insère les lignes dans DynamoDB avec une clé composite"""
    if not items:
        print(f"Aucun item à insérer dans {table_name}.")
        return

    table = dynamodb.Table(table_name)
    with table.batch_writer() as batch:
        for item in items:
            item = {k: (v if v is not None else "") for k, v in item.items()}
            titre = item.get("Titre", "")
            station_id = str(item.get("station_id", "") or "")
            nom_lieu = item.get("Nom_du_lieu", "")
            item["composite_key"] = f"{station_id}_{nom_lieu}"
            batch.put_item(Item=item)

    print(f"{len(items)} éléments insérés dans {table_name}.")


def lambda_handler(event, context):
    print("Démarrage du job DataMart Loader (vidage + réinsertion)")

    today_csv_key = get_latest_csv_key(S3_BUCKET, S3_PREFIX)
    rows = parse_csv_from_s3(S3_BUCKET, today_csv_key)

    table_name = os.environ.get("TABLE_NAME", "datamart_fusion_csv")
    table = create_table_if_not_exists(
        table_name,
        key_schema=[
            {"AttributeName": "Titre", "KeyType": "HASH"},
            {"AttributeName": "composite_key", "KeyType": "RANGE"},
        ],
        attr_defs=[
            {"AttributeName": "Titre", "AttributeType": "S"},
            {"AttributeName": "composite_key", "AttributeType": "S"},
        ],
    )

    clear_table(table_name)

    insert_items(table_name, rows)

    print(f"Job DataMart terminé pour le fichier du jour : {today_csv_key}")
    return {
        "statusCode": 200,
        "body": f"{len(rows)} lignes insérées dans {table_name} depuis {today_csv_key}"
    }
