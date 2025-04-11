# chatbot lab

## Set up environment:
1. AWS CLI: Ensure AWS CLI is installed and configured on your laptop(refer to the setup guide provided in Session 1).
2. Ensure python is installed: python 3.8 or higher.




## Part 1: 

### Step 1: Object storage Creation
Go to the Part1 folder: `cd Part1`

Install required python libraries listed in the 'requirements.txt': `pip3 install -r requirements.txt`

Create an S3 bucket and upload a few PDF files by running: 

`python3 create-S3-and-put-docs.py --bucket_name [YourBucketName] --local_path [PathToYourPDFFiles]`

Where placeholders:
- **[YourBucketName]**: The name for the new S3 bucket to be created.
- **[PathToYourPDFFiles]**: The local directory path where the PDF files are stored.


### Step 2: Vector Store Creation

Create a vector database for storing embeddings by running: 

`python3 create-vector-db.py --collection_name [Name_of_colletion] --iam_user [YourIAM_user] --acount_id [YourAccount_ID]`

Where: 
- **[Name_of_colletion]**: Name of the collection that you want to create.
- **[YourIAM_user]** : the IAM user is `CloudSys-group-XX`, with "XX" representing your group number.
- **[YourAccount_ID]** : the ACCOUNT ID of your account.


This script performs the following actions:

* Sets up encryption, network, and data access policies for the collection.
* Creates a vector store with the name collection entered as argument.
* After the vector store is set up, the script retrieves and displays the store's endpoint.

### Step 3: Vectorizing the PDF Files: 

After setting up the S3 bucket and Vector DB, we could process PDF files to generate and store embeddings in the vector database.

Start by requesting access to the following models on the AWS Bedrock service:

- Titan Embedding v1
- Claude v2

Then, run: 

`python3 vectorise-store.py --bucket_name [YourBucketName] --endpoint [YourVectorDBEndpoint] --index_name [Index_name] --local_path [local_path]`

Where: 

- **[YourBucketName]**: The name of the S3 bucket containing the PDF files.
- **[YourVectorDBEndpoint]**: Endpoint of the vector database.
- **[Index_name]**: The index_name where to store the embeddings in the collection.
- **[local_path]**: local_path  

The vectorise-store.py script will:

* Download PDF files from the S3 bucket.
* Split them into chunks.
* Generate embeddings from the chunks.
* Create an index in the vector DB.
* Store these embeddings in the OpenSearch Vector DB.


## Part 2:

### Step 1: Preparation

Go to the Part1 folder: `cd Part2`

Install required python libraries listed in the 'requirements.txt': `pip3 install -r requirements.txt`

Before deploying the chatbot on an EC2 instance, complete the following preliminary steps:

1. Create a Key Pair: This key pair will be used for SSH access to your EC2 instance.

2. Create a Security Group: Define rules to allow the instance to be accessible externally. The security group should include the following rules:
    - For inbound rules: you need to allow SSH traffic, HTTP/HTTPs traffic and open port 8501 used by the application.
    - Outbound Rules: Allow all traffic.

3.Create a `config.ini` file under Part2 folder with the following content:


    [aws]
    aws_access_key_id = YOUR_AWS_ACCESS_KEY_ID
    aws_secret_access_key = YOUR_AWS_SECRET_ACCESS_KEY
    region = us-east-1

    [opensearch]
    endpoint = YOUR_OPENSEARCH_ENDPOINT
    index_name = YOUR_INDEX_NAME 


### Step 2: Launching the Instance

Use the provided create_instance.py script to deploy your EC2 instance with the essential startup configurations. Before executing this, adjust Security Group and Key Pair already created in the first step.

In the `ec2.create_instance` we have the following parameters: 

- ImageId: this is a custom Amazon Machine Image (AMI) that contains all the configurations and dependencies required for the chatbot application. For this lab, we have already created this image: `ami-08919ae65ab65be94`. Please use it as parameter.
- UserData:  is used to run script after the instance starts. The script will put the credentials in the instance so that the instance can aceess other services in AWS, the endpoint of the Vector DB, and the index name. Then the script will run the application.

    This is the script: 

    ```yaml
    f"""#!/bin/bash
    cat <<EOT > /home/ubuntu/chatbot-lab/Part2/config.ini
    {config_content}
    EOT
    source /home/ubuntu/chatbotlab/bin/activate
    ## Run the apllication 
    cd /home/ubuntu/chatbot-lab/Part2
    streamlit run chatbot.py 
    """

    ````

Run the following command to create your instance:

`python3 create_instance.py --ami_id "ami-08919ae65ab65be94" --key_pair_name [KeyPairName] --security_group_id [SecurityGroupID]`

Where: 

- **[KeyPairName]**: The name of the key_pair created earlier.
- **[SecurityGroupID]**: The id of the security group created earlier.

## Step 3: Accessing the application

Once the app starts, navigate to this URL `http://[public_ip_adress_of_yourVM]:8501` in your web browser to start interacting with your chatbot