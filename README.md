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

Where placeholders:
- **[YourBucketName]**: The name for the new S3 bucket to be created.
- **[PathToYourPDFFiles]**: The local directory path where the PDF files are stored.


### Step 2: Vector Store Creation
Create a vector database for storing embeddings by running: 

`python3 create-vector-db.py --collection_name [Name_of_colletion] --iam_user [YourIAM_user]`

Where placeholders: 
- **[Name_of_colletion]**: Name of the collection that you want to create to store embeddings.
- **[YourIAM_user]** : For example for group 14 the iam_user is `master-group-14`


This script performs the following actions:

* Sets up encryption, network, and data access policies for the collection.
* Creates a vector store with the name collection entered as argument.
* After the vector store is set up, the script retrieves and displays the store's endpoint for immediate use.

### Step 3: Vectorizing the PDF Files
After setting up the S3 bucket and Vector Store, we could process PDF files to generate and store embeddings in the vector database.

Run: 

`python3 main.py --bucket_name [YourBucketName] --endpoint [YourVectorDBEndpoint] --index_name [Index_name] --local_path [local_path]`

Where placeholders: 

- **[YourBucketName]**: The name of the S3 bucket containing the PDF files.
- **[YourVectorDBEndpoint]**: Endpoint for the vector database.
- **[Index_name]**: The index_name where to store the embeddings in the collection.
- **[local_path]**: local_path  

The main.py script will:

* Download PDF files from the S3 bucket.
* Split them into chunks.
* Generate embeddings from the chunks.
* Create an index in the vector DB.
* Store these embeddings in the OpenSearch Vector DB.


## Part 2:

### Step 1: Preparation
Before deploying the chatbot on an EC2 instance, complete the following preliminary steps:

1. Create a Key Pair: This key pair will be used for SSH access to your EC2 instance whe you need it.

2. Create a Security Group: Define rules to allow the instance to be accessible externally. The security group should include the following rules:
    - For inbound rules: you need to allow SSH traffic, HTTP/HTTPs trafic and 8501 for streamlit.
    - Outbound Rules: Allow all traffic.

* Prepare config.ini:

Ensure your config.ini file includes your AWS credentials (aws_access_key_id, aws_secret_access_key, region), with the region set to 'us-east-1'. Also, include the endpoint and index_name for the OpenSearch service established earlier.

### Step 2: Launching the Instance

Utilize the provided create_instance.py script to deploy your EC2 instance with the essential startup configurations. Before executing this, adjust Security Group and Key Pair already created in the first step.

In the `ec2.create_instance` we have the following parameters: 

- ImageId: `ami-03a1012f7ddc87219`, this is a custom Amazon Machine Image (AMI) that contains all the configurations and dependencies required for the chatbot application.
- UserData:  is used to run script after the instance starts. The script will put the credentials in the instance so that the instance can aceess other services in AWS, and the endpoint for the Vector DB, index name. Then the script will run the application.

    This is the script: 

    ```yaml
    script = f"""#!/bin/bash
    cat <<EOT > /home/ubuntu/chatbot-lab/Part\ 2/config.ini
    {config_content}
    EOT
    source /home/ubuntu/chatbotlab/bin/activate
    ## Run the apllication 
    cd /home/ubuntu/chatbot-lab/Part\ 2
    streamlit run main.py 

    ````

Run the following command to create your instance:

`python3 create_instance.py`

## Step 3: Accessing the app:

Once the app starts, navigate to this URL `http://[public_ip_adress_of_yourVM]:8501` in your web browser to start interacting with your chatbot