import json
from get_line_reports import lambda_handler as get_line_reports
from get_station_velib import lambda_handler as get_station_velib

def lambda_handler(event, context):

    """Orchestre les deux fonctions Lambda locales"""
    
    print("=== Démarrage du job Bronze Layer ===")

    try:
        get_line_reports(event, context)
        print("get_line_reports exécuté avec succès.")
    except Exception as e:
        print(f"Erreur dans get_line_reports : {e}")

    print("Exécution de get_station_velib...")
    try:
        get_station_velib(event, context)
        print("get_station_velib exécuté avec succès.")
    except Exception as e:
        print(f"Erreur dans get_station_velib : {e}")

    return {
        "statusCode": 200,
        "body": json.dumps("====== Tous les jobs ont été exécutés ! ======")
    }
