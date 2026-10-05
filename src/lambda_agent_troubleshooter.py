import boto3
import json

logs = boto3.client("logs")
lambda_client = boto3.client("lambda")
dynamodb = boto3.client("dynamodb")

APP_FUNCTION = "task-app"
LOG_GROUP = "/aws/lambda/task-app"
TABLE_NAME = "appdata"


def get_cloudwatch_logs():
    response = logs.filter_log_events(
        logGroupName=LOG_GROUP,
        filterPattern="ERROR",
        limit=20
    )

    return [
        event["message"]
        for event in response.get("events", [])
    ]


def get_lambda_configuration():
    response = lambda_client.get_function_configuration(
        FunctionName=APP_FUNCTION
    )

    return {
        "function_name": response["FunctionName"],
        "runtime": response.get("Runtime"),
        "environment": response.get("Environment", {}).get("Variables", {})
    }


def describe_dynamodb_table():
    response = dynamodb.describe_table(
        TableName=TABLE_NAME
    )

    return {
        "table_name": response["Table"]["TableName"],
        "status": response["Table"]["TableStatus"],
        "arn": response["Table"]["TableArn"]
    }


def update_lambda_configuration(table_name):
    response = lambda_client.update_function_configuration(
        FunctionName=APP_FUNCTION,
        Environment={
            "Variables": {
                "TABLE_NAME": table_name
            }
        }
    )

    return {
        "function_name": response["FunctionName"],
        "status": response["LastUpdateStatus"],
        "TABLE_NAME": table_name
    }

def verify_lambda_configuration(expected_table_name):
    response = lambda_client.get_function_configuration(
        FunctionName=APP_FUNCTION
    )

    actual_table_name = (
        response.get("Environment", {})
        .get("Variables", {})
        .get("TABLE_NAME")
    )

    return {
        "verified": actual_table_name == expected_table_name,
        "expected_TABLE_NAME": expected_table_name,
        "actual_TABLE_NAME": actual_table_name,
        "update_status": response.get("LastUpdateStatus")
    }

def wait_for_lambda_update(max_attempts=10):
    import time

    for _ in range(max_attempts):
        response = lambda_client.get_function_configuration(
            FunctionName=APP_FUNCTION
        )

        status = response.get("LastUpdateStatus")

        if status == "Successful":
            return True

        if status == "Failed":
            return False

        time.sleep(1)

    return False

def verify_application():
    response = lambda_client.invoke(
        FunctionName=APP_FUNCTION,
        InvocationType="RequestResponse",
        Payload=b"{}"
    )

    payload = json.loads(response["Payload"].read())

    application_ok = (
        response["StatusCode"] == 200
        and "FunctionError" not in response
        and payload.get("statusCode") == 200
    )

    return {
        "verified": application_ok,
        "lambda_status_code": response["StatusCode"],
        "application_status_code": payload.get("statusCode"),
        "response": payload
    }

def simulate_claude(evidence):
    configured_table = (
        evidence["lambda_configuration"]
        ["environment"]
        .get("TABLE_NAME")
    )

    actual_table = evidence["dynamodb_table"]["table_name"]

    if configured_table != actual_table:
        return {
            "status": "ROOT_CAUSE_IDENTIFIED",
            "root_cause": (
                f"Lambda task-app is configured to use DynamoDB table "
                f"'{configured_table}', but the application table is "
                f"'{actual_table}'."
            ),
            "proposed_remediation": {
                "action": "update_lambda_configuration",
                "function": "task-app",
                "environment_variable": "TABLE_NAME",
                "current_value": configured_table,
                "proposed_value": actual_table
            },
            "requires_human_approval": True
        }

    return {
        "status": "NO_ROOT_CAUSE_IDENTIFIED",
        "requires_human_approval": False
    }

def lambda_handler(event, context):
    #evidence = {
    #    "cloudwatch_logs": get_cloudwatch_logs(),
    #    "lambda_configuration": get_lambda_configuration(),
    #    "dynamodb_table": describe_dynamodb_table()
    #}

    #return {
    #    "statusCode": 200,
    #    "body": json.dumps(evidence, default=str)
    #}
    evidence = {
        "cloudwatch_logs": get_cloudwatch_logs(),
        "lambda_configuration": get_lambda_configuration(),
        "dynamodb_table": describe_dynamodb_table()
    }

    diagnosis = simulate_claude(evidence)

    remediation = None
    verification = None
    application_verification = None

    if (
        event.get("approved") is True
        and diagnosis["status"] == "ROOT_CAUSE_IDENTIFIED"
        and diagnosis.get("requires_human_approval") is True
    ):
        proposed_value = diagnosis["proposed_remediation"]["proposed_value"]
        remediation = update_lambda_configuration(proposed_value)
        wait_for_lambda_update()
        verification = verify_lambda_configuration(proposed_value)
        application_verification = verify_application()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "evidence": evidence,
            "diagnosis": diagnosis,
            "remediation": remediation,
            "verification": verification,
            "application_verification": application_verification
        }, default=str)
    }
