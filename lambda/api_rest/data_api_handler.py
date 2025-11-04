import json
import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb")

TABLES = {
    "evenements": "datamart_evenements",
    "velib": "datamart_velib_evenements",
    "ratp": "datamart_ratp",
    "evenements_ratp_velib": "datamart_fusion_csv"
}


def scan_table(table_name, filters=None):
    """Scan complet d'une table DynamoDB avec filtres dynamiques"""
    table = dynamodb.Table(table_name)

    filter_expr = None
    if filters:
        for key, value in filters.items():
            condition = Attr(key).eq(value)
            filter_expr = condition if filter_expr is None else filter_expr & condition

    # Scan avec ou sans filtre
    scan_args = {"FilterExpression": filter_expr} if filter_expr else {}
    response = table.scan(**scan_args)
    items = response.get("Items", [])

    # Gestion pagination
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"], **scan_args)
        items.extend(response.get("Items", []))

    return items


def lambda_handler(event, context):
    print(f"Requête API : {json.dumps(event)}")

    path = event.get("path", "/").strip("/")
    http_method = event.get("httpMethod", "GET")
    query_params = event.get("queryStringParameters") or {}

    if http_method != "GET":
        return {
            "statusCode": 405,
            "body": json.dumps({"error": "Méthode non autorisée"}),
        }

    if path in ("evenements", "velib", "velib_evenements", "ratp", "evenements_ratp_velib"):
        table_key = "velib" if path in ("velib", "velib_evenements") else path
        data = scan_table(TABLES[table_key], filters=query_params)
    else:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Endpoint non trouvé"}),
        }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data, ensure_ascii=False)
    }
