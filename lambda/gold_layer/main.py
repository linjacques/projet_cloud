import json
from datamarts import lambda_handler as datamarts_handler
from s3_csv_loader import lambda_handler as s3_csv_handler  

def lambda_handler(event, context):
    """
    Orchestration de deux jobs (séquentielle).
    """
    print("=== Démarrage du job DataMart Global ===")

    print("Exécution du script datamarts.py")
    try:
        datamarts_handler(event, context)
        print("datamarts exécuté avec succès.")
    except Exception as e:
        print(f"Erreur dans datamarts : {e}")

    print("Exécution du script s3_csv-loader.py")
    try:
        s3_csv_handler(event, context)
        print("velib_loader exécuté avec succès.")
    except Exception as e:
        print(f"Erreur dans velib_loader : {e}")

    print("=== Tous les jobs DataMart terminés ===")

    return {
        "statusCode": 200,
        "body": json.dumps("====== Tous les jobs ont été exécutés avec succès ======")
    }
