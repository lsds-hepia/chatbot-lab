# chatbot-lab

## Set up environment
1. AWS CLI: Ensure AWS CLI is installed and configured on your laptop(refer to the setup guide provided in Session 1).
2. Ensure python is installed: python 3.8 or higher.
3. Install required python libraries listed in the 'requirements.txt': 

`pip3 install -r requirements.txt`


## Part 1: 

### Step 1: Object storage Creation
Create an S3 bucket and upload a few PDF files by running: 

`python3 create-S3-and-put-docs.py --bucket_name [YourBucketName] --local_path [PathToYourPDFFiles]`

Where:
- **--bucket_name**: The name for the new S3 bucket to be created.
- **--local_path**: The local directory path where the PDF files are stored.


### Step 2: Vector Store Creation
Create a vector database for storing embeddings by running: 

`python3 create-vector-db.py --collection_name [Name_of_colletion] --iam_user [YourIAM_user]`

Where: 
- **--collection_name**: Name of the collection that you want to create to store embeddings.
- **--iam_user** : For example for group 14 the iam_user is `master-group-14`


This script performs the following actions:

* Sets up encryption, network, and data access policies for the collection.
* Creates a vector store with the name collection entered as argument.
* After the vector store is set up, the script retrieves and displays the store's endpoint for immediate use.

### Step 3: Vectorizing the PDF Files
After setting up the S3 bucket and Vector Store, we could process PDF files to generate and store embeddings in the vector database.

Run: 

`python3 main.py --bucket_name [YourBucketName] --endpoint [YourVectorDBEndpoint] --index_name [Index_name] --local_path [local_path]`

Where: 

- **--bucket_name**: The name of the S3 bucket containing the PDF files.
- **--endpoint**: Endpoint for the vector database.
- **--index_name**: The index_name where to store the embeddings in the collection.
- **--local_path**: local_path  

The main.py script will:

* Download PDF files from the S3 bucket.
* Split them into chunks.
* Generate embeddings from the chunks.
* Create an index in the vector DB.
* Store these embeddings in the OpenSearch Vector DB.


## Part 2:

