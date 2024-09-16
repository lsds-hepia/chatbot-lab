# Creator: Abir Chebbi (abir.chebbi@hesge.ch)
## Source: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-sdk.html


import boto3
import botocore
import time
import argparse


client = boto3.client('opensearchserverless')
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


def createAccessPolicy(client, policy_name, collection_name, IAM_USER):
    """Creates a data access policy for the specified collection."""
    try:
        policy_content = f"""
        [
            {{
                "Rules": [
                    {{
                        "Resource": ["collection/{collection_name}"],
                        "Permission": [
                            "aoss:CreateCollectionItems",
                            "aoss:DeleteCollectionItems",
                            "aoss:UpdateCollectionItems",
                            "aoss:DescribeCollectionItems"
                        ],
                        "ResourceType": "collection"
                    }},
                    {{
                        "Resource": ["index/{collection_name}/*"],
                        "Permission": [
                            "aoss:CreateIndex",
                            "aoss:DeleteIndex",
                            "aoss:UpdateIndex",
                            "aoss:DescribeIndex",
                            "aoss:ReadDocument",
                            "aoss:WriteDocument"
                        ],
                        "ResourceType": "index"
                    }}
                ],
                "Principal": ["arn:aws:iam::352909266144:user/{IAM_USER}"]
            }}
        ]
        """
        response = client.create_access_policy(
            description=f'Data access policy for {collection_name}',
            name=policy_name,
            policy=policy_content,
            type='data'
        )
        print('\nAccess policy created:')
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print('[ConflictException] An access policy with this name already exists.')
        else:
            raise error

        

        
def waitForCollectionCreation(client,collection_name):
    """Waits for the collection to become active"""
    time.sleep(30)
    response = client.batch_get_collection(
            names=[collection_name])
    print('\nCollection successfully created:')
    print(response["collectionDetails"])
    # Extract the collection endpoint from the response
    host = (response['collectionDetails'][0]['collectionEndpoint'])
    final_host = host.replace("https://", "")
    return final_host


def main(collection_name,IAM_USER):
    encryption_policy_name = f'{collection_name}-encryption-policy'
    network_policy_name = f'{collection_name}-network-policy'
    access_policy_name = f'{collection_name}-access-policy'
    createEncryptionPolicy(client, encryption_policy_name, collection_name)
    createNetworkPolicy(client, network_policy_name, collection_name)
    createAccessPolicy(client, access_policy_name, collection_name,IAM_USER)
    collection = client.create_collection(name=collection_name,type='VECTORSEARCH')
    ENDPOINT= waitForCollectionCreation(client,collection_name)

    print("Collection created successfully:", collection)
    print("Collection ENDPOINT:", ENDPOINT)

if __name__== "__main__":
    parser = argparse.ArgumentParser(description="Create collection")
    parser.add_argument("--collection_name", help="The name of the collection")
    parser.add_argument("--iam_user", help="The iam user")
    args = parser.parse_args()
    main(args.collection_name,args.iam_user)
