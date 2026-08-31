# Creator: Abir Chebbi (abir.chebbi@hesge.ch)
## Source: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-sdk.html


import boto3
import botocore
import json
import time
import argparse


#service = 'aoss'

def createEncryptionPolicy(client,policy_name, collection_name):
    """Creates an encryption policy for the specified collection."""
    try:
        response = client.create_security_policy(
            description=f'Encryption policy for {collection_name}',
            name=policy_name,
            policy=f"""
                {{
                    \"Rules\": [
                        {{
                            \"ResourceType\": \"collection\",
                            \"Resource\": [
                                \"collection/{collection_name}\"
                            ]
                        }}
                    ],
                    \"AWSOwnedKey\": true
                }}
                """,
            type='encryption'
        )
        print('\nEncryption policy created:')
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] The policy name or rules conflict with an existing policy.')
        else:
            raise error


def createNetworkPolicy(client,policy_name,collection_name):
    """Creates a network policy for the specified collection."""
    try:
        response = client.create_security_policy(
            description=f'Network policy for {collection_name}',
            name=policy_name,
            policy=f"""
                [{{
                    \"Description\": \"Public access for {collection_name}\",
                    \"Rules\": [
                        {{
                            \"ResourceType\": \"dashboard\",
                            \"Resource\": [\"collection/{collection_name}\"]                            
                        }},
                        {{
                            \"ResourceType\": \"collection\",
                            \"Resource\": [\"collection/{collection_name}\"]                            
                        }}
                    ],
                    \"AllowFromPublic\": true
                }}]
                """,
            type='network'
        )
        print('\nNetwork policy created:')
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] A network policy with this name already exists.')
        else:
            raise error


def createAccessPolicy(client, policy_name, collection_name, MY_ARN, TASK_ROLE_ARN):
    """Creates a data access policy for the specified collection."""

    ## You run Part 1 yourself. The application runs on a server in Parts 2 and 3 and
    ## uses the role, which OpenSearch treats as a different principal, so it is listed too.
    principals = [MY_ARN]
    if TASK_ROLE_ARN:
        principals.append(TASK_ROLE_ARN)

    policy = [
        {
            "Rules": [
                {
                    "Resource": [f"collection/{collection_name}"],
                    "Permission": [
                        "aoss:CreateCollectionItems",
                        "aoss:DeleteCollectionItems",
                        "aoss:UpdateCollectionItems",
                        "aoss:DescribeCollectionItems"
                    ],
                    "ResourceType": "collection"
                },
                {
                    "Resource": [f"index/{collection_name}/*"],
                    "Permission": [
                        "aoss:CreateIndex",
                        "aoss:DeleteIndex",
                        "aoss:UpdateIndex",
                        "aoss:DescribeIndex",
                        "aoss:ReadDocument",
                        "aoss:WriteDocument"
                    ],
                    "ResourceType": "index"
                }
            ],
            "Principal": principals
        }
    ]

    try:
        response = client.create_access_policy(
            description=f'Data access policy for {collection_name}',
            name=policy_name,
            policy=json.dumps(policy),
            type='data'
        )
        print('\nAccess policy created for:', principals)
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print('[ConflictException] An access policy with this name already exists.')
        else:
            raise error


def waitForCollectionCreation(client, collection_name):
    """Waits for the collection to become active."""
    for attempt in range(60):
        time.sleep(10)
        response = client.batch_get_collection(names=[collection_name])
        details = response.get('collectionDetails', [])
        if details and details[0]['status'] == 'ACTIVE':
            print('\nCollection successfully created:')
            print(details)
            host = details[0]['collectionEndpoint']
            return host.replace("https://", "")
        status = details[0]['status'] if details else 'CREATING'
        print(f"  waiting for collection to become ACTIVE (status: {status})...")
    raise SystemExit("Collection did not become ACTIVE in 10 minutes; check the console.")


def main(collection_name, region, TASK_ROLE_ARN):
    client = boto3.client('opensearchserverless', region_name=region)

    ## Your own identity, so you do not have to type it
    MY_ARN = boto3.client('sts', region_name=region).get_caller_identity()['Arn']
    print("Granting access to:", MY_ARN)
    encryption_policy_name = f'{collection_name}-encryption-policy'
    network_policy_name = f'{collection_name}-network-policy'
    access_policy_name = f'{collection_name}-access-policy'
    createEncryptionPolicy(client, encryption_policy_name, collection_name)
    createNetworkPolicy(client, network_policy_name, collection_name)
    createAccessPolicy(client, access_policy_name, collection_name, MY_ARN, TASK_ROLE_ARN)
    collection = client.create_collection(name=collection_name,type='VECTORSEARCH')
    ENDPOINT= waitForCollectionCreation(client,collection_name)

    print("Collection created successfully:", collection)
    print("Collection ENDPOINT:", ENDPOINT)

if __name__== "__main__":
    parser = argparse.ArgumentParser(description="Create collection")
    parser.add_argument("--collection_name", required=True, help="The name of the collection")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--task_role_arn", default=None,
                        help="ARN of the role the application uses in Parts 2 and 3")
    args = parser.parse_args()
    main(args.collection_name, args.region, args.task_role_arn)
