# Creator: Abir Chebbi (abir.chebbi@hesge.ch)



import boto3
import os
import argparse


def create_bucket(s3_client, bucket_name):
    """ Create an S3 bucket """
    print("Creating Bucket")
    response = s3_client.create_bucket(Bucket=bucket_name)
    print(response)
    print()


# Function to write files to S3
def write_files(s3_client, directory, bucket):
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

def main(bucket_name, local_dir):
    s3_client = boto3.client('s3')
    create_bucket(s3_client, bucket_name)
    write_files(s3_client, local_dir, bucket_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload PDF files to an S3 bucket")
    parser.add_argument("--bucket_name", help="The name of the S3 bucket to which the files will be uploaded")
    parser.add_argument("--local_path", help="The name of the folder to put the pdf files")
    args = parser.parse_args()
    main(args.bucket_name, args.local_path)

