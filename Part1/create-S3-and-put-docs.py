# Creator: Abir Chebbi (abir.chebbi@hesge.ch)

import boto3
import botocore
import os
import argparse


def create_bucket(s3_client, bucket_name, region):
    """ Create an S3 bucket """
    print("Creating Bucket")
    try:
        if region == 'us-east-1':
            response = s3_client.create_bucket(Bucket=bucket_name)
        else:
            response = s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(response)
    except botocore.exceptions.ClientError as error:
        code = error.response['Error']['Code']
        if code == 'BucketAlreadyOwnedByYou':
            print(f"Bucket '{bucket_name}' already exists in your account, reusing it.")
        elif code in ('BucketAlreadyExists', 'IllegalLocationConstraintException'):
            ## S3 bucket names are unique across all AWS accounts worldwide
            raise SystemExit(
                f"\nThe bucket name '{bucket_name}' is already taken by someone else.\n"
                f"S3 bucket names are globally unique, so pick a different one, for example\n"
                f"by adding your account ID: --bucket_name {bucket_name}-<your_account_id>"
            )
        else:
            raise
    print()


# Function to write files to S3
def write_files(s3_client, directory, bucket):
    if not os.path.isdir(directory):
        raise SystemExit(f"Local path '{directory}' does not exist.")
    count = 0
    for filename in os.listdir(directory):
        if filename.endswith(".pdf"):  # Check if the file is a PDF
            file_path = os.path.join(directory, filename)
            with open(file_path, 'rb') as file:
                print(f"Uploading {filename} to bucket {bucket}...")
                s3_client.put_object(
                    Body=file,
                    Bucket=bucket,
                    Key=filename
                )
                print(f"{filename} uploaded successfully.")
                count += 1
    if count == 0:
        raise SystemExit(f"No PDF files found in '{directory}'. Nothing was uploaded.")
    print(f"\nUploaded {count} PDF file(s).")


def main(bucket_name, local_dir, region):
    s3_client = boto3.client('s3', region_name=region)
    create_bucket(s3_client, bucket_name, region)
    write_files(s3_client, local_dir, bucket_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload PDF files to an S3 bucket")
    parser.add_argument("--bucket_name", required=True, help="The name of the S3 bucket to which the files will be uploaded")
    parser.add_argument("--local_path", required=True, help="The folder containing the PDF files to upload")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    args = parser.parse_args()
    main(args.bucket_name, args.local_path, args.region)
