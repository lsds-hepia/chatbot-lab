## Source: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-sdk.html
import boto3
import botocore
import time


client = boto3.client('opensearchserverless')
service = 'aoss'
Vector_store_name='test2'

def createEncryptionPolicy(client):
    """Creates an encryption policy that matches all collections beginning with test"""
    try:
        response = client.create_security_policy(
            description='Encryption policy for test collections',
            name='test-policy',
            policy="""
                {
                    \"Rules\":[
                        {
                            \"ResourceType\":\"collection\",
                            \"Resource\":[
                                \"collection\/test*\"
                            ]
                        }
                    ],
                    \"AWSOwnedKey\":true
                }
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


def createNetworkPolicy(client):
    """Creates a network policy that matches all collections beginning with test"""
    try:
        response = client.create_security_policy(
            description='Network policy for Test collections',
            name='test-policy',
            policy="""
                [{
                    \"Description\":\"Public access for Test collection\",
                    \"Rules\":[
                        {
                            \"ResourceType\":\"dashboard\",
                            \"Resource\":[\"collection\/test*\"]
                        },
                        {
                            \"ResourceType\":\"collection\",
                            \"Resource\":[\"collection\/test*\"]
                        }
                    ],
                    \"AllowFromPublic\":true
                }]
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


def createAccessPolicy(client):
    """Creates a data access policy that matches all collections beginning with test"""
    try:
        response = client.create_access_policy(
            description='Data access policy for Test collections',
            name='test-policy',
            policy="""
                [{
                    \"Rules\":[
                        {
                            \"Resource\":[
                                \"index\/test*\/*\"
                            ],
                            \"Permission\":[
                                \"aoss:CreateIndex\",
                                \"aoss:DeleteIndex\",
                                \"aoss:UpdateIndex\",
                                \"aoss:DescribeIndex\",
                                \"aoss:ReadDocument\",
                                \"aoss:WriteDocument\"
                            ],
                            \"ResourceType\": \"index\"
                        },
                        {
                            \"Resource\":[
                                \"collection\/test*\"
                            ],
                            \"Permission\":[
                                \"aoss:CreateCollectionItems\",
                                \"aoss:DeleteCollectionItems\",
                                \"aoss:UpdateCollectionItems\",
                                \"aoss:DescribeCollectionItems\"
                            ],
                            \"ResourceType\": \"collection\"
                        }
                    ],
                    \"Principal\":[
                        \"arn:aws:iam::768034348959:user/AbirChebbi\"
                    ]
                }]
                """,
            type='data'
        )
        print('\nAccess policy created:')
        print(response)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] An access policy with this name already exists.')
        else:
            raise error
        

        
def waitForCollectionCreation(client):
    """Waits for the collection to become active"""
    time.sleep(40)
    response = client.batch_get_collection(
            names=['test1'])
    print('\nCollection successfully created:')
    print(response["collectionDetails"])
    # Extract the collection endpoint from the response
    host = (response['collectionDetails'][0]['collectionEndpoint'])
    final_host = host.replace("https://", "")
    return final_host


def main():

    createEncryptionPolicy(client)
    createNetworkPolicy(client)
    createAccessPolicy(client)
    collection = client.create_collection(name=Vector_store_name,type='VECTORSEARCH')
    ENDPOINT= waitForCollectionCreation(client)

    print("Collection created successfully:", collection)
    print("Collection ENDPOINT:", ENDPOINT)

if __name__== "__main__":
    main()