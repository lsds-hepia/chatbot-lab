# Creator: Abir Chebbi (abir.chebbi@hesge.ch)


import boto3

BUCKET_NAME = ''

S3_CLIENT = boto3.client('s3')
S3_RESOURCE = boto3.resource('s3')

# # # Delete Bucket

# First, delete all objects in the Bucket
bucket = S3_RESOURCE.Bucket(BUCKET_NAME)

print("Deleting all objects in Bucket\n")
bucket.objects.all().delete()


print("Deleting Bucket")
# Bucket Deletion
response = S3_CLIENT.delete_bucket(
    Bucket=BUCKET_NAME 

)

print(response)
