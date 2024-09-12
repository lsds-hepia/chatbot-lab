# chatbot-lab

## Set up environment
1. AWS CLI: Ensure AWS CLI is installed and configured on your laptop(refer to the setup guide provided in Session 1).
2. Ensure python is installed: python 3.8 or higher.
3. Install required python libraries listed in the 'requirements.txt': 

`pip3 install -r requirements.txt`


## Part 1: 

### Step 1: Object storage Creation
Create an S3 bucket and upload a few PDF files by running: 

`python create-S3-and-put-docs.py --bucket_name [YourBucketName] --local_path [PathToYourPDFFiles]`

Where:
- **--bucket_name**: The name for the new S3 bucket to be created.
- **--local_path**: The local directory path where the PDF files are stored.


### Step 2: Vector Store Creation
Create a vector database for storing embeddings by running: 

`python create-vector-db.py --collection_name [Name_of_colletion] --IAM_user [YourIAM_User]`

Where: 
- **--collection_name**: Name of the collection that you want to create to store embeddings.
- **--IAM_USER** : For example for group 14 the IAM USER = master-group-14


This script performs the following actions:

* Sets up encryption, network, and data access policies for the collection.
* Creates a vector store with the name collection entered as argument.
* After the vector store is set up, the script retrieves and displays the store's endpoint for immediate use.

### Step 3: Vectorizing the PDF Files
After setting up the S3 bucket and Vector Store, we could process PDF files to generate and store embeddings in the vector database.

Run: 

`python main.py --bucket_name [YourBucketName] --endpoint [YourVectorDBEndpoint]`

Where: 

- **--bucket_name**: The name of the S3 bucket containing the PDF files.
- **--endpoint**: Endpoint for the vector database.
- **--index_name**: The index_name where to store the embeddings in the collection.

The main.py script will:
1. Download PDF files from the S3 bucket.
2. Split them into chunks.
3. Generate embeddings from the chunks.
4. Create an index in the vector DB.
5. Store these embeddings in the OpenSearch Vector DB.


## Part 2:

