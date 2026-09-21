# Creator: Abir Chebbi (abir.chebbi@hesge.ch)
#
# Deletes the collection and the policies created by create-vector-db.py.
# A collection keeps costing money until it is deleted, so always run this
# at the end of the lab.

import boto3
import botocore
import time
import argparse



def delete_collection(client, collection_name):
    """Deletes the collection and waits for it to disappear."""
    try:
        response = client.batch_get_collection(names=[collection_name])
        details = response.get('collectionDetails', [])
        if not details:
            print(f"No collection named '{collection_name}' found (already deleted?).")
            return
        collection_id = details[0]['id']
        client.delete_collection(id=collection_id)
        print(f"Deleting collection '{collection_name}' (id: {collection_id})...")
    except botocore.exceptions.ClientError as error:
        print(f"Could not delete collection: {error}")
        return

    ## The policies can only be deleted once the collection is gone
    for _ in range(30):
        time.sleep(10)
        response = client.batch_get_collection(names=[collection_name])
        if not response.get('collectionDetails'):
            print("Collection deleted.")
            return
        print("  still deleting...")
    print("WARNING: collection still present after 5 minutes; check the console.")


def delete_policy(client, kind, name):
    """Deletes one security or access policy."""
    try:
        if kind == 'data':
            client.delete_access_policy(name=name, type='data')
        else:
            client.delete_security_policy(name=name, type=kind)
        print(f"Deleted {kind} policy: {name}")
    except botocore.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"{kind} policy '{name}' not found (already deleted?).")
        else:
            print(f"Could not delete {kind} policy '{name}': {error}")


def main(collection_name, region):
    client = boto3.client('opensearchserverless', region_name=region)
    confirm = input(
        f"Permanently delete collection '{collection_name}' and its policies? "
        f"All stored embeddings will be lost. [y/N] "
    )
    if confirm.strip().lower() != 'y':
        print("Aborted.")
        return

    delete_collection(client, collection_name)
    delete_policy(client, 'encryption', f'{collection_name}-encryption-policy')
    delete_policy(client, 'network', f'{collection_name}-network-policy')
    delete_policy(client, 'data', f'{collection_name}-access-policy')
    print("\nTeardown complete. Verify in the console that no collection remains billing.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete the vector DB collection and its policies")
    parser.add_argument("--collection_name", required=True, help="The name of the collection to delete")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    args = parser.parse_args()
    main(args.collection_name, args.region)
