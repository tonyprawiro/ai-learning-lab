import boto3
import json

logs = boto3.client("logs")
lambda_client = boto3.client("lambda")
dynamodb = boto3.client("dynamodb")
bedrock = boto3.client("bedrock-runtime", region_name="ap-southeast-1")
MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

TOOLS = [
        {
            "toolSpec": {
                "name": "get_lambda_configuration",
                "description": (
                    "Get the current AWS Lambda configuration for the "
                    "task-app application, including its environment variables"
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "get_cloudwatch_logs",
                "description": (
                    "Retrieve recent Cloudwatch log events for the task-app"
                    "Lambda function to investigate application errors"
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "describe_dynamodb_table",
                "description": (
                    "Get information about the DynamoDB table used by the "
                    "task-app application, including its name, stats, and ARN."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "update_lambda_configuration",
                "description": (
                    "Update the TABLE_NAME environment variable of the task-app "
                    "Lambda function. This is a remediation action and must only "
                    "be used after explicit human approval."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": ("The DynamoDB table name to configure as TABLE_NAME")
                            }
                        },
                        "required": ["table_name"]
                    }
                }
            }
        }
]

SYSTEM_PROMPT = """
You are an AWS application troubleshooting agent responsible for diagnosing failures affecting the task-app Lambda application.

Use the available tools to gather evidence and determine the root cause.

Rules:
1. Gather sufficient evidence before identifying a root cause.
2. Do not assume that an AccessDeniedError means IAM permissions should be expanded.
3. Inspect and compare application configuration with the actual AWS resources.
4. Prefer correcting an incorrect configuration over weakening security controls.
5. Never use a remediation tool unless explicit human approval has been provided.
6. Do not claim that remediation succeeded until the application has been verified.
7. Base conclusions only on evidence obtained through the available tools.
"""

def call_claude(messages):
    return bedrock.converse(
        modelId=MODEL_ID,
        system=[
            {
                "text": SYSTEM_PROMPT
            }
        ],
        messages=messages,
        toolConfig={
            "tools": TOOLS
        },
        inferenceConfig={
            "temperature": 0,
            "maxTokens": 1000
        }
    )

def run_agent(messages):
    while True:
        response = call_claude(messages)
        assistant_message = response["output"]["message"]
        messages.append(assistant_message)
        if response["stopReason"] != "tool_use":
            return response
        tool_results = []
        for content in assistant_message["content"]:
            if "toolUse" not in content:
                continue
            tool_use = content["toolUse"]
            result = execute_tool(
                tool_use["name"],
                tool_use.get("input", {})
            )
            tool_results.append({
                "toolResult": {
                    "toolUseId": tool_use["toolUseId"],
                    "content": [
                        {
                            "json": result
                        }
                    ]
                }
            })
        messages.append({
            "role": "user",
            "content": tool_results
        })

def test_claude_agent():
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": (
                        "Investigate why the task-app application is failing. "
                        "Use the available tools to gather evidence. "
                        "Do not perform any remediation."
                    )
                }
            ]
        }
    ]
    response = run_agent(messages)
    return response["output"]["message"]

def execute_tool(tool_name, tool_input):
    if tool_name == "get_lambda_configuration":
        return get_lambda_configuration()
    if tool_name == "get_cloudwatch_logs":
        return get_cloudwatch_logs()
    if tool_name == "describe_dynamodb_table":
        return describe_dynamodb_table()
    if tool_name == "update_lambda_configuration":
        return update_lambda_configuration(tool_input["table_name"])
    raise ValueError(f"Unknown tool: {tool_name}")

APP_FUNCTION = "task-app"
LOG_GROUP = "/aws/lambda/task-app"
TABLE_NAME = "appdata"


def get_cloudwatch_logs():
    response = logs.filter_log_events(
        logGroupName=LOG_GROUP,
        filterPattern="ERROR",
        limit=20
    )

    return {
        "log_events": [
            event["message"]
            for event in response.get("events", [])
        ]
    }


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

    if event.get("test_claude") is True:
        result = test_claude_agent()
        return {
            "statuscode": 200,
            "body": json.dumps(result, default=str)
        }

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
