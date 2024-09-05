# chatbot-lab

## Set up environment
1. AWS CLI: Ensure AWS CLI is installed and configured on your laptop(refer to Session 1)
2. Ensure python is installed: python 3.8 or higher
2. Install required python libraries listed in the 'requirements.txt': 
`pip install -r requirement.txt`


## Part 1: 

### Step 1: Object storage Creation
Create an S3 bucket and upload a few PDF files (Detailed steps are provided in the first session).

### Step 2: Vector Store Creation
To set up the Vector Store, run the following command: `python Create-Vector-DB.py`

This script performs the following actions:

* Set up the security policies: Sets up encryption, network, and data access policies for collections starting with "test".
* Vector Store Initialization: Creates a vector store named test1, specifically designed for vector search operations.
* Endpoint Retrieval: After the vector store is set up, the script retrieves and displays the store's endpoint for immediate use.

### Step 3: Vectorizing the PDF Files
After setting up the S3 bucket and Vector Store, prepare to vectorize the PDF files:
* In main.py, update the S3 bucket name to the one you created.
* Update the Vector Store endpoint with the one provided by the setup script.
* Execute the processing script: `python main.py`

The main.py script will:
1. Download PDF files from the S3 bucket.
2. Split them into chunks.
3. Generate embeddings from the chunks.
4. Store these embeddings in the OpenSearch Vector DB.