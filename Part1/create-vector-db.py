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
        # First, check if policy already exists
        try:
            existing_policy = client.get_security_policy(name=policy_name, type='encryption')
            print(f'\nEncryption policy "{policy_name}" already exists:')
            print(existing_policy)
            return existing_policy
        except botocore.exceptions.ClientError as check_error:
            if check_error.response['Error']['Code'] != 'ResourceNotFoundException':
                raise check_error
            # Policy doesn't exist, create it
            pass
        
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
        return response
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] The policy name or rules conflict with an existing policy.')
            return None
        elif error.response['Error']['Code'] == 'ServiceQuotaExceededException':
            print(f'[ServiceQuotaExceededException] Too many encryption policies. Consider cleaning up unused policies.')
            print(f'Current limit: 150 encryption policies per account')
            print(f'You can list policies with: aws opensearchserverless list-security-policies --type encryption')
            return None
        else:
            print(f"Error creating encryption policy: {error}")
            return None


def createNetworkPolicy(client,policy_name,collection_name):
    """Creates a network policy for the specified collection."""
    try:
        # First, check if policy already exists
        try:
            existing_policy = client.get_security_policy(name=policy_name, type='network')
            print(f'\nNetwork policy "{policy_name}" already exists:')
            print(existing_policy)
            return existing_policy
        except botocore.exceptions.ClientError as check_error:
            if check_error.response['Error']['Code'] != 'ResourceNotFoundException':
                raise check_error
            # Policy doesn't exist, create it
            pass
            
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
        return response
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(
                '[ConflictException] A network policy with this name already exists.')
            return None
        elif error.response['Error']['Code'] == 'ServiceQuotaExceededException':
            print(f'[ServiceQuotaExceededException] Too many network policies. Consider cleaning up unused policies.')
            print(f'You can list policies with: aws opensearchserverless list-security-policies --type network')
            return None
        else:
            print(f"Error creating network policy: {error}")
            return None


def createAccessPolicy(client, policy_name, collection_name, IAM_USER,ACCOUNT_ID):
    """Creates a data access policy for the specified collection."""
    
    # Debug: Print the values being used
    print(f"Debug - IAM_USER: {IAM_USER}")
    print(f"Debug - ACCOUNT_ID: {ACCOUNT_ID}")
    
    # Build the principal ARN
    user_arn = f"arn:aws:iam::{ACCOUNT_ID}:user/{IAM_USER}"
    print(f"Debug - User ARN: {user_arn}")
    
    try:
        # First, check if policy already exists
        try:
            existing_policy = client.get_access_policy(name=policy_name, type='data')
            print(f'\nAccess policy "{policy_name}" already exists:')
            print(existing_policy)
            return existing_policy
        except botocore.exceptions.ClientError as check_error:
            if check_error.response['Error']['Code'] != 'ResourceNotFoundException':
                raise check_error
            # Policy doesn't exist, create it
            pass
        
        # Create policy using string replacement to avoid f-string issues
        policy_template = '''[
    {
        "Rules": [
            {
                "Resource": ["collection/COLLECTION_NAME"],
                "Permission": [
                    "aoss:CreateCollectionItems",
                    "aoss:DeleteCollectionItems",
                    "aoss:UpdateCollectionItems",
                    "aoss:DescribeCollectionItems"
                ],
                "ResourceType": "collection"
            },
            {
                "Resource": ["index/COLLECTION_NAME/*"],
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
        "Principal": ["PRINCIPAL_ARN"]
    }
]'''
        
        # Replace placeholders
        principal_arn = f"arn:aws:iam::{ACCOUNT_ID}:root"
        policy_content = policy_template.replace("COLLECTION_NAME", collection_name)
        policy_content = policy_content.replace("USER_ARN", user_arn)
        policy_content = policy_content.replace("PRINCIPAL_ARN", principal_arn)
        
        print(f"Debug - Final policy content: {policy_content}")
        
        response = client.create_access_policy(
            description=f'Data access policy for {collection_name}',
            name=policy_name,
            policy=policy_content,
            type='data'
        )
        print('\nAccess policy created:')
        print(response)
        return response
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print('[ConflictException] An access policy with this name already exists.')
            return None
        elif error.response['Error']['Code'] == 'ServiceQuotaExceededException':
            print(f'[ServiceQuotaExceededException] Too many access policies. Consider cleaning up unused policies.')
            print(f'You can list policies with: aws opensearchserverless list-access-policies --type data')
            return None
        else:
            print(f"Error creating access policy: {error}")
            return None

        

        
def waitForCollectionCreation(client,collection_name):
    """Waits for the collection to become active"""
    max_retries = 20  # Maximum number of retries (10 minutes with 30s intervals)
    retry_count = 0
    
    while retry_count < max_retries:
        time.sleep(30)
        response = client.batch_get_collection(names=[collection_name])
        collection_details = response["collectionDetails"][0]
        
        print(f'\nCollection status check {retry_count + 1}:')
        print(f'Status: {collection_details.get("status", "UNKNOWN")}')
        
        if collection_details.get("status") == "ACTIVE":
            print('\nCollection successfully created:')
            print(collection_details)
            
            # Check if collectionEndpoint exists
            if 'collectionEndpoint' in collection_details:
                host = collection_details['collectionEndpoint']
                final_host = host.replace("https://", "")
                return final_host
            else:
                print("Warning: Collection is ACTIVE but endpoint not yet available")
        
        retry_count += 1
        print(f"Collection still creating... waiting 30 more seconds ({retry_count}/{max_retries})")
    
    raise Exception(f"Collection did not become active within {max_retries * 30} seconds")


def verify_aws_identity(IAM_USER, ACCOUNT_ID):
    """Verify the AWS account ID using STS caller identity"""
    try:
        # Get current identity from STS (doesn't require IAM permissions)
        sts_client = boto3.client('sts')
        identity = sts_client.get_caller_identity()
        current_account = identity['Account']
        current_arn = identity['Arn']
        current_user_id = identity['UserId']
        
        print(f"Current AWS Account ID: {current_account}")
        print(f"Current User ARN: {current_arn}")
        print(f"Current User ID: {current_user_id}")
        print(f"Provided Account ID: {ACCOUNT_ID}")
        
        # Use the current account ID instead of the provided one
        if current_account != ACCOUNT_ID:
            print(f"INFO: Using current account ID ({current_account}) instead of provided ({ACCOUNT_ID})")
            ACCOUNT_ID = current_account
        
        # Extract username from ARN if it's a user ARN
        if ":user/" in current_arn:
            actual_username = current_arn.split("/")[-1]
            print(f"Detected IAM username from ARN: {actual_username}")
            
            if actual_username != IAM_USER:
                print(f"INFO: Using actual username ({actual_username}) instead of provided ({IAM_USER})")
                IAM_USER = actual_username
        elif ":role/" in current_arn:
            print("Running as IAM role, using role ARN for permissions")
        else:
            print("Running as root user or unknown identity type")
            
        print(f"Identity verification successful!")
        print(f"Final Account ID: {current_account}")
        print(f"Final IAM User: {IAM_USER}")
        
        return True, current_account, IAM_USER  # Return account ID and corrected username
            
    except Exception as e:
        print(f"Error verifying AWS identity: {e}")
        return False, ACCOUNT_ID, IAM_USER


def main(collection_name,IAM_USER,ACCOUNT_ID):
    # Verify AWS identity before proceeding
    identity_verified, correct_account_id, correct_iam_user = verify_aws_identity(IAM_USER, ACCOUNT_ID)
    if not identity_verified:
        print("AWS identity verification failed. Exiting.")
        return
    
    # Use the correct account ID and IAM user
    ACCOUNT_ID = correct_account_id
    IAM_USER = correct_iam_user
    print(f"Using Account ID: {ACCOUNT_ID}")
    print(f"Using IAM User: {IAM_USER}")
    
    # Check if collection already exists
    try:
        existing_collection = client.batch_get_collection(names=[collection_name])
        if existing_collection['collectionDetails']:
            collection_details = existing_collection['collectionDetails'][0]
            print(f'\nCollection "{collection_name}" already exists:')
            print(f'Status: {collection_details.get("status", "UNKNOWN")}')
            if 'collectionEndpoint' in collection_details:
                host = collection_details['collectionEndpoint']
                final_host = host.replace("https://", "")
                print("Collection ENDPOINT:", final_host)
                return final_host
            else:
                print("Collection exists but endpoint not available yet")
                return None
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            print(f"Error checking for existing collection: {e}")
            return
        # Collection doesn't exist, continue with creation
        pass
    
    encryption_policy_name = f'{collection_name}-encryption-policy'
    network_policy_name = f'{collection_name}-network-policy'
    access_policy_name = f'{collection_name}-access-policy'
    
    print(f"\nCreating policies for collection: {collection_name}")
    
    # Create policies and check they were created successfully
    encryption_result = createEncryptionPolicy(client, encryption_policy_name, collection_name)
    if not encryption_result:
        print("ERROR: Failed to create or find encryption policy. Cannot proceed.")
        return
    
    network_result = createNetworkPolicy(client, network_policy_name, collection_name)
    if not network_result:
        print("ERROR: Failed to create or find network policy. Cannot proceed.")
        return
        
    access_result = createAccessPolicy(client, access_policy_name, collection_name,IAM_USER,ACCOUNT_ID)
    if not access_result:
        print("ERROR: Failed to create or find access policy. Cannot proceed.")
        return
    
    print("All policies created/verified successfully!")
    
    # Wait a moment for policies to propagate
    print("Waiting 10 seconds for policies to propagate...")
    time.sleep(10)
    
    print(f"\nCreating collection: {collection_name}")
    try:
        collection = client.create_collection(name=collection_name,type='VECTORSEARCH')
        print("Collection creation initiated:", collection)
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ConflictException':
            print(f'[ConflictException] Collection "{collection_name}" already exists.')
            # Try to get the existing collection details
            existing_collection = client.batch_get_collection(names=[collection_name])
            if existing_collection['collectionDetails']:
                collection_details = existing_collection['collectionDetails'][0]
                if 'collectionEndpoint' in collection_details:
                    host = collection_details['collectionEndpoint']
                    final_host = host.replace("https://", "")
                    print("Collection ENDPOINT:", final_host)
                    return final_host
        else:
            raise error
    
    ENDPOINT = waitForCollectionCreation(client,collection_name)
    print("Collection created successfully!")
    print("Collection ENDPOINT:", ENDPOINT)
    return ENDPOINT

if __name__== "__main__":
    parser = argparse.ArgumentParser(description="Create collection")
    parser.add_argument("--collection_name", help="The name of the collection")
    parser.add_argument("--iam_user", help="The iam user")
    parser.add_argument("--account_id", help="The account id")
    args = parser.parse_args()
    main(args.collection_name,args.iam_user,args.account_id)
