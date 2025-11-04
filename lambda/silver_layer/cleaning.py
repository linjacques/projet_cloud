import json
import csv
import boto3
import io
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

s3 = boto3.client("s3")

BUCKET_SOURCE = "proj-cloud-brute"
BUCKET_DEST = "proj-cloud-argent"


def lire_csv_s3(bucket, key):
    """Lit un fichier CSV depuis S3"""
    obj = s3.get_object(Bucket=bucket, Key=key)
    contenu = obj["Body"].read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(contenu))
    return [row for row in reader]


def lire_json_s3(bucket, key):
    """Lit un fichier JSON depuis S3"""
    obj = s3.get_object(Bucket=bucket, Key=key)
    contenu = obj["Body"].read().decode("utf-8")
    return json.loads(contenu)


def trouver_dernier_fichier(bucket, prefix):
    """Trouve le fichier le plus récent dans un préfixe S3"""
    res = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if "Contents" not in res:
        return None
    fichiers = sorted(res["Contents"], key=lambda x: x["LastModified"], reverse=True)
    return fichiers[0]["Key"] if fichiers else None


def calcul_distance(lat1, lon1, lat2, lon2):
    """Calcule la distance (en mètres) entre deux points"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def trouver_stations_proches(lat, lon, stations, n=3):
    """Renvoie les N stations Vélib les plus proches d’un point"""
    distances = []
    for s in stations:
        try:
            d = calcul_distance(float(lat), float(lon), float(s["lat"]), float(s["lon"]))
            distances.append({
                "station_id": s["station_id"],
                "station_name": s["station_name"],
                "distance_m": round(d, 2),
                "velib_disponibles": int(s.get("num_bikes_available", 0)),
                "bornes_libres": int(s.get("num_docks_available", 0))
            })
        except Exception:
            continue
    distances.sort(key=lambda x: x["distance_m"])
    return distances[:n]


def status_evenement(occurrences):
    """Détermine si un événement est en cours ou passé"""
    if not occurrences:
        return "inconnu"
    now = datetime.now(ZoneInfo("Europe/Paris"))
    blocs = occurrences.split(";")
    for bloc in blocs:
        if "_" in bloc:
            debut_str, fin_str = bloc.split("_")
            try:
                debut = datetime.fromisoformat(debut_str.strip()).replace(tzinfo=ZoneInfo("Europe/Paris")) - timedelta(hours=2)
                fin = datetime.fromisoformat(fin_str.strip()).replace(tzinfo=ZoneInfo("Europe/Paris")) + timedelta(hours=2)
                if debut <= now <= fin:
                    return "active"
            except Exception:
                continue
    return "past"


def lambda_handler(event, context):
    print("=== Lecture des sources depuis S3 ===")

    evenements_key = "que-faire-a-paris-v2.csv"
    evenements = lire_csv_s3(BUCKET_SOURCE, evenements_key)
    print(f"{len(evenements)} événements chargés depuis {evenements_key}")

    date_du_jour = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
    prefix_velib_info = f"velib/station_information/{date_du_jour}/"
    prefix_velib_status = f"velib/station_status/{date_du_jour}/"
    info_key = trouver_dernier_fichier(BUCKET_SOURCE, prefix_velib_info)
    status_key = trouver_dernier_fichier(BUCKET_SOURCE, prefix_velib_status)
    print(f"Derniers fichiers Vélib :\n- {info_key}\n- {status_key}")

    info_json = lire_json_s3(BUCKET_SOURCE, info_key)
    status_json = lire_json_s3(BUCKET_SOURCE, status_key)

    info_stations = info_json.get("data", {}).get("stations", info_json.get("stations", []))
    status_stations = status_json.get("data", {}).get("stations", status_json.get("stations", []))

    info_dict = {s["station_id"]: s for s in info_stations}
    status_dict = {s["station_id"]: s for s in status_stations}

    stations = []
    for station_id, info in info_dict.items():
        if station_id in status_dict:
            merged = {**info, **status_dict[station_id]}
            stations.append({
                "station_id": merged["station_id"],
                "station_name": merged["name"],
                "lat": merged["lat"],
                "lon": merged["lon"],
                "num_bikes_available": merged.get("num_bikes_available", 0),
                "num_docks_available": merged.get("num_docks_available", 0)
            })
    print(f"Fusion Vélib réussie : {len(stations)} stations")

    evenement_important = [
        "Théâtre du Châtelet", "Théâtre de la Porte Saint-Martin", "Théâtre de la Madeleine",
    "Théâtre du Rond-Point", "Théâtre de la Ville", "Le 13e Art", "Le Dôme de Paris – Palais des Sports",
    "Accor Arena", "La Défense Arena", "Le Grand Rex Paris", "Le Casino de Paris",
    "Palais Garnier (Opéra de Paris)", "L’Olympia – Bruno Coquatrix", "Cirque d’Hiver Bouglione",
    "Théâtre de Suresnes Jean Vilar", "Théâtre de la Cité internationale", "Philharmonie de Paris",
    "La Cigale", "La Bellevilloise", "Le Trianon", "Le Bataclan", "Le Point Ephémère",
    "Supersonic", "Cabaret Sauvage", "Petit Bain", "La Seine Musicale", "Le Zénith de Paris",
    "Le Bus Palladium", "Stade Roland-Garros", "Stade Pierre de Coubertin", "Stade Jean Bouin",
    "Stade du Parc des Princes", "Adidas Arena", "Centre sportif Georges Carpentier",
    "Paris Expo Porte de Versailles", "Parc des Expositions de Villepinte", "Musée du Louvre",
    "Musée d’Orsay", "Musée du quai Branly – Jacques Chirac", "Cité des Sciences et de l’Industrie",
    "Cité de la Musique", "Grand Palais", "Petit Palais", "Palais de la Découverte",
    "Fondation Louis Vuitton", "Parc de la Villette", "Parc Floral de Paris", "Bois de Vincennes",
    "Bois de Boulogne", "Jardin du Luxembourg", "Place de la Concorde", "Champ-de-Mars",
    "Parvis de l’Hôtel de Ville", "Parc des Buttes-Chaumont", "Place de la Nation", "Sorbonne Nouvelle",
    "Université Paris Cité", "Cité Internationale Universitaire de Paris", "Maison de la Radio et de la Musique",
    "Institut du Monde Arabe", "UNESCO"
    ]

    events_filtered = [e for e in evenements if e.get("Nom du lieu") in evenement_important]
    print(f"{len(events_filtered)} événements filtrés importants")

    results_evenements = []
    for ev in events_filtered:
        coords = ev.get("Coordonnées géographiques", "").strip()
        coords = coords.replace("[", "").replace("]", "").replace(" ", "")
        if not coords or "," not in coords:
            continue

        try:
            lat, lon = map(float, coords.split(","))
        except ValueError:
            continue

        if lat == 0.0 and lon == 0.0:
            continue

        proches = trouver_stations_proches(lat, lon, stations, n=3)
        for p in proches:
            results_evenements.append({
                "Titre": ev.get("Titre", ""),
                "Nom_du_lieu": ev.get("Nom du lieu", ""),
                "Ville": ev.get("Ville", "Paris"),
                "date_heure": ev.get("Occurrences", ""),
                "lat_event": lat,
                "lon_event": lon,
                **p,
                "severity_name": "",
                "line_name": "",
                "main_message": "",
                "type_source": "evenement",
                "status": status_evenement(ev.get("Occurrences", ""))
            })
    print(f"{len(results_evenements)} événements enrichis avec Vélib")

    prefix_ratp = f"trafic_metro/bronze/streaming/{date_du_jour}/"
    dernier_ratp = trouver_dernier_fichier(BUCKET_SOURCE, prefix_ratp)
    ratp_data = lire_json_s3(BUCKET_SOURCE, dernier_ratp)
    ratp_results = []

    for row in ratp_data:
        if "impacted_objects" in row and row["impacted_objects"]:
            obj = row["impacted_objects"][0]
            coord_from = obj.get("impacted_section", {}).get("from", {}).get("stop_area", {}).get("coord")
            if coord_from and "lat" in coord_from and "lon" in coord_from:
                lat = float(coord_from["lat"])
                lon = float(coord_from["lon"])
                proches = trouver_stations_proches(lat, lon, stations, n=3)

                main_message = ""
                if "messages" in row and row["messages"]:
                    for msg in row["messages"]:
                        if msg.get("channel", {}).get("name") == "titre":
                            main_message = msg.get("text", "")
                            break

                line_name = obj.get("pt_object", {}).get("line", {}).get("code", "")
                severity_name = row.get("severity", {}).get("name", "")

                for p in proches:
                    ratp_results.append({
                        "Titre": f"Perturbation {row.get('id', '')}",
                        "Nom_du_lieu": obj.get("pt_object", {}).get("name", ""),
                        "Ville": "Paris",
                        "date_heure": datetime.now(ZoneInfo("Europe/Paris")).isoformat(),
                        "lat_event": lat,
                        "lon_event": lon,
                        **p,
                        "severity_name": severity_name,
                        "line_name": line_name,
                        "main_message": main_message,
                        "type_source": "ratp",
                        "status": row.get("status", "")
                    })

    print(f"{len(ratp_results)} perturbations RATP enrichies avec Vélib")

    fusion_finale = results_evenements + ratp_results
    print(f"{len(fusion_finale)} lignes finales à enregistrer")

    output_key = f"evenements_ratp_velib/fusion_{date_du_jour}.csv"
    csv_buffer = io.StringIO()
    colonnes = list(fusion_finale[0].keys()) if fusion_finale else []

    writer = csv.DictWriter(csv_buffer, fieldnames=colonnes)
    writer.writeheader()
    writer.writerows(fusion_finale)

    s3.put_object(
        Bucket=BUCKET_DEST,
        Key=output_key,
        Body=csv_buffer.getvalue().encode("utf-8"),
        ContentType="text/csv"
    )

    print(f"Fichier final enregistré : s3://{BUCKET_DEST}/{output_key}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Fusion terminée avec succès",
            "output": f"s3://{BUCKET_DEST}/{output_key}",
            "rows": len(fusion_finale),
            "evenements": len(results_evenements),
            "ratp": len(ratp_results)
        })
    }
