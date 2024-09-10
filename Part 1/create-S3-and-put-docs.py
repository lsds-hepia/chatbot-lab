import boto3
import os

LOCAL_DIR = "pdfs"
BUCKET_NAME = 'cloud-lecture-nabil-2024-25'

# Initiate S3 client
s3_client = boto3.client('s3')

# Create S3 Bucket
print("Creating Bucket")
response = s3_client.create_bucket(
    Bucket=BUCKET_NAME,
)
print(response)
print()

# Function to write files to S3
def write_files(directory, bucket):
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

# Upload PDF files to S3 bucket
print("Writing Items to Bucket")
write_files(LOCAL_DIR, BUCKET_NAME)

