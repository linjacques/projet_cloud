import boto3
import csv
import io
import time

S3_BUCKET = "proj-cloud-argent"
S3_PREFIX = "evenements_ratp_velib/" 
DYNAMODB = boto3.resource("dynamodb")

TABLES = {
    "ratp": "datamart_ratp",
    "evenements": "datamart_evenements",
    "velib_evenements": "datamart_velib_evenements"
}


def get_latest_csv_key(bucket, prefix):
    """Retourne le dernier CSV (le plus récent) dans le dossier S3 donné"""
    s3 = boto3.client("s3")
    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if "Contents" not in response:
        raise FileNotFoundError(f"Aucun fichier trouvé dans {prefix}")

    csv_files = [obj for obj in response["Contents"] if obj["Key"].endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError(f"Aucun fichier CSV trouvé dans {prefix}")

    latest_file = max(csv_files, key=lambda x: x["LastModified"])
    print(f"Dernier fichier trouvé : {latest_file['Key']}")
    return latest_file["Key"]


def parse_csv_from_s3(bucket, key):
    """Charge et parse un CSV depuis S3 (gestion BOM + nettoyage)"""
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(data))
    rows = [
        {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()}
        for r in reader
    ]
    return rows


def clear_table(table):
    """Vide une table DynamoDB sans la supprimer (équivalent TRUNCATE)"""
    print(f"Vidage de la table '{table.name}'...")
    scan_kwargs = {}
    deleted = 0

    while True:
        response = table.scan(**scan_kwargs)
        items = response.get("Items", [])
        if not items:
            break

        with table.batch_writer() as batch:
            for item in items:
                # On supprime en utilisant les clés définies dans le schéma
                key = {k["AttributeName"]: item[k["AttributeName"]] for k in table.key_schema if k["AttributeName"] in item}
                batch.delete_item(Key=key)
                deleted += 1

        if "LastEvaluatedKey" not in response:
            break
        scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    print(f"Table '{table.name}' vidée ({deleted} éléments supprimés).")


def insert_items(table, items):
    """Insère ou met à jour les éléments dans une table DynamoDB"""
    if not items:
        print(f"Aucun item à insérer dans {table.name}.")
        return

    with table.batch_writer(overwrite_by_pkeys=[key["AttributeName"] for key in table.key_schema]) as batch:
        for item in items:
            batch.put_item(Item=item)

    print(f"{len(items)} lignes insérées/actualisées dans {table.name}.")


def lambda_handler(event, context):
    print("=== Démarrage Lambda DataMart Builder ===")

    latest_csv_key = get_latest_csv_key(S3_BUCKET, S3_PREFIX)
    rows = parse_csv_from_s3(S3_BUCKET, latest_csv_key)
    print(f"{len(rows)} lignes chargées depuis {latest_csv_key}")

    ratp_table = DYNAMODB.Table(TABLES["ratp"])
    events_table = DYNAMODB.Table(TABLES["evenements"])
    velib_table = DYNAMODB.Table(TABLES["velib_evenements"])

    clear_table(ratp_table)
    clear_table(events_table)
    clear_table(velib_table)

    events, velib_events, ratp_records = [], [], []

    for row in rows:
        type_source = row.get("type_source", "").lower()

        if type_source == "evenement":
            events.append({
                "Nom_du_lieu": row.get("Nom_du_lieu", ""),
                "Titre": row.get("Titre", ""),
                "Ville": row.get("Ville", ""),
                "date_heure": row.get("date_heure", ""),
                "type_source": type_source,
                "status": row.get("status", ""),
            })

        velib_events.append({
            "station_id": str(row.get("station_id", "")),
            "Titre": row.get("Titre", ""),
            "station_name": row.get("station_name", ""),
            "lat_event": row.get("lat_event", ""),
            "lon_event": row.get("lon_event", ""),
            "distance_m": row.get("distance_m", ""),
            "velib_disponibles": row.get("velib_disponibles", ""),
            "bornes_libres": row.get("bornes_libres", ""),
            "Nom_du_lieu": row.get("Nom_du_lieu", ""),
        })

        if type_source == "ratp":
            ratp_records.append({
                "line_name": row.get("line_name", "N/A"),
                "updated_at": row.get("date_heure", ""),
                "status": row.get("status", ""),
                "severity_name": row.get("severity_name", ""),
                "duration_min": row.get("duration_min", ""),
                "main_message": row.get("main_message", ""),
                "Ville": row.get("Ville", ""),
                "Nom_du_lieu": row.get("Nom_du_lieu", ""),
                "type_source": type_source,
            })

    insert_items(events_table, events)
    insert_items(velib_table, velib_events)
    insert_items(ratp_table, ratp_records)

    print("=== Datamart reconstruit avec succès ===")
    return {
        "status": "success",
        "evenements_count": len(events),
        "velib_count": len(velib_events),
        "ratp_count": len(ratp_records),
        "last_csv": latest_csv_key
    }
