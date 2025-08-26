# Creator: Abir Chebbi (abir.chebbi@hesge.ch)



import boto3
import os
import argparse


def create_bucket(s3_client, bucket_name):
    """ Create an S3 bucket """
    print("Creating Bucket")
    
    # Convert bucket name to lowercase to meet AWS requirements
    bucket_name = bucket_name.lower()
    print(f"Using bucket name: {bucket_name}")
    
    # Get the region from the client
    region = s3_client.meta.region_name
    
    # Create bucket with location constraint if not in us-east-1
    if region == 'us-east-1':
        response = s3_client.create_bucket(Bucket=bucket_name)
    else:
        response = s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )
    
    print(response)
    print()


# Function to write files to S3
def write_files(s3_client, path, bucket):
    if os.path.isfile(path):
        # Handle single file
        filename = os.path.basename(path)
        if filename.endswith(".pdf"):  # Check if the file is a PDF
            with open(path, 'rb') as file:
                print(f"Uploading {filename} to bucket {bucket}...")
                s3_client.put_object(
                    Body=file,
                    Bucket=bucket,
                    Key=filename
                )
                print(f"{filename} uploaded successfully.")
        else:
            print(f"Skipping {filename} - not a PDF file")
    elif os.path.isdir(path):
        # Handle directory
        for filename in os.listdir(path):
            if filename.endswith(".pdf"):  # Check if the file is a PDF
                file_path = os.path.join(path, filename)
                with open(file_path, 'rb') as file:
                    print(f"Uploading {filename} to bucket {bucket}...")
                    s3_client.put_object(
                        Body=file,
                        Bucket=bucket,
                        Key=filename
                    )
                    print(f"{filename} uploaded successfully.")
    else:
        print(f"Error: {path} is neither a file nor a directory")

def main(bucket_name, local_dir):
    s3_client = boto3.client('s3')
    # Convert bucket name to lowercase to meet AWS requirements
    bucket_name = bucket_name.lower()
    create_bucket(s3_client, bucket_name)
    write_files(s3_client, local_dir, bucket_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload PDF files to an S3 bucket")
    parser.add_argument("--bucket_name", help="The name of the S3 bucket to which the files will be uploaded")
    parser.add_argument("--local_path", help="The path to a PDF file or directory containing PDF files")
    args = parser.parse_args()
    main(args.bucket_name, args.local_path)

