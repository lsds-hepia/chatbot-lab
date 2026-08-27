# chatbot lab

Build a RAG chatbot on AWS: store lecture PDFs in **S3**, embed them with **Bedrock**,
index the vectors in **OpenSearch Serverless**, and serve a **Streamlit** chat UI from **EC2**.

> ### Before you start: two IDs you must look up yourself
> Model IDs change between regions and over time. Open **Bedrock > Model access** in your
> region and note the exact IDs for:
> - an **embedding** model (e.g. `amazon.titan-embed-text-v2:0`)
> - a current **Claude** chat model
>
> Request access to both if it is not already granted. The scripts take these as
> parameters -- do not assume the defaults are available in your region.

> ### Cost warning
> An **OpenSearch Serverless collection bills continuously** for a minimum number of
> OCU-hours, whether or not you are querying it. When you finish the lab, run
> `Part1/delete-vector-db.py` **and** `Part1/delete-s3.py`, and terminate your EC2 instance.

## Set up environment:
1. Use your credentials to create an Ubuntu 24.04 specific VM on the AWS Amazon portal
2. AWS CLI: Ensure AWS CLI is installed and configured on the VM you just created (refer to the setup guide provided in Session 1).
3. Ensure python is installed: **python 3.10 or higher** (required by langchain-core 1.x, langchain-aws, streamlit and boto3). Ubuntu 24.04 ships 3.12, so the stock VM is fine.

## Part 1:

Go to the Part1 folder: `cd Part1`

Install required python libraries listed in the 'requirements.txt': `pip3 install -r requirements.txt`

### Step 1: Object storage Creation

Create an S3 bucket and upload a few PDF files by running:

`python3 create-S3-and-put-docs.py --bucket_name [YourBucketName] --local_path [PathToYourPDFFiles]`

Where placeholders:
- **[YourBucketName]**: The name for the new S3 bucket to be created.
- **[PathToYourPDFFiles]**: The local directory path where the PDF files are stored.

Optional: `--region` (default `us-east-1`).

### Step 2: Vector Store Creation

Create a vector database for storing embeddings by running:

`python3 create-vector-db.py --collection_name [Name_of_collection] --iam_user [YourIAM_user] --account_id [YourAccount_ID]`

Where:
- **[Name_of_collection]**: Name of the collection that you want to create.
- **[YourIAM_user]** : the IAM user of your account.
- **[YourAccount_ID]** : the ACCOUNT ID of your account.

You will find YourIAM_user and YourAccount_ID when you click on your account ID in the top right-hand corner of the AWS Amazon portal.

The script performs the following actions:

* Sets up encryption, network, and data access policies for the collection.
* Creates a vector store with the name collection entered as argument.
* Waits for the collection to become ACTIVE, then displays the store's endpoint.

**Copy the endpoint it prints** -- you need it in Step 3 and in Part 2.

### Step 3: Vectorizing the PDF Files:

After setting up the S3 bucket and Vector DB, we process the PDF files to generate and
store embeddings in the vector database.

Make sure your embedding model is enabled in **Bedrock > Model access** (see the note at
the top of this README), then run:

`python3 vectorise-store.py --bucket_name [YourBucketName] --endpoint [YourVectorDBEndpoint] --index_name [Index_name] --local_path [local_path]`

Where:

- **[YourBucketName]**: The name of the S3 bucket containing the PDF files.
- **[YourVectorDBEndpoint]**: Endpoint of the vector database (without `https://`).
- **[Index_name]**: The index_name where to store the embeddings in the collection.
- **[local_path]**: local folder the PDFs are downloaded into.

Optional: `--region`, and `--embed_model_id` if you are not using the default
`amazon.titan-embed-text-v2:0`.

The vectorise-store.py script will:

* Download PDF files from the S3 bucket.
* Split them into chunks.
* Generate embeddings from the chunks.
* Create an index in the vector DB, sized to match your embedding model.
* Store these embeddings in the OpenSearch Vector DB.

> The index is sized from the embedding model (Titan v1 gives 1536 dimensions, v2 gives
> 1024). If you change the model, use a new `--index_name`.


## Part 2:

### Step 1: Preparation

Go to the Part2 folder: `cd Part2`

Install required python libraries listed in the 'requirements.txt': `pip3 install -r requirements.txt`

Before deploying the chatbot on an EC2 instance, complete the following preliminary steps:

1. **Create a Key Pair**: This key pair will be used for SSH access to your EC2 instance.

2. **Create a Security Group**: Define rules to allow the instance to be accessible externally. The security group should include the following rules:
    - For inbound rules: you need to allow SSH traffic, HTTP/HTTPs traffic and open port 8501 used by the application.
    - Outbound Rules: Allow all traffic.

3. **Create the config file**: copy `config.ini.example` to `config.ini` and fill it in:

    ```ini
    [aws]
    region = us-east-1
    aws_access_key_id = YOUR_AWS_ACCESS_KEY_ID
    aws_secret_access_key = YOUR_AWS_SECRET_ACCESS_KEY

    [opensearch]
    endpoint = YOUR_OPENSEARCH_ENDPOINT
    index_name = YOUR_INDEX_NAME

    [bedrock]
    embed_model_id = amazon.titan-embed-text-v2:0
    chat_model_id = PUT_A_CURRENT_CLAUDE_MODEL_ID_HERE
    ```

   `config.ini` is gitignored. Never commit it.

### Step 2: Launching the Instance

Use the provided `create_instance.py` script to deploy your EC2 instance with the essential
startup configurations.

- **ImageId**: a custom Amazon Machine Image (AMI) containing the lab code and its
  dependencies at `/home/ubuntu/chatbot-lab`. Ask your instructor for the current AMI ID
  for your region.

  > **Instructors:** the instance runs the copy of `chatbot.py` baked into the AMI, not this
  > repository. After updating this repo you must rebuild the AMI (updated code at
  > `/home/ubuntu/chatbot-lab`, and a venv at `/home/ubuntu/chatbotlab` with the current
  > `Part2/requirements.txt` installed), otherwise students still run the old app.
- **UserData**: a script run once at first boot. It writes `config.ini` onto the instance,
  creates the virtualenv if the AMI does not already have one, and starts the application.
  Everything it does is logged to `/var/log/chatbot-lab.log`.

Run the following command to create your instance:

`python3 create_instance.py --ami_id [AMI_ID] --key_pair_name [KeyPairName] --security_group_id [SecurityGroupID]`

Where:

- **[AMI_ID]**: The AMI provided by your instructor.
- **[KeyPairName]**: The name of the key_pair created earlier.
- **[SecurityGroupID]**: The id of the security group created earlier.

Optional: `--instance_type` (default `t3.micro`).

The script waits for the instance to start and prints its public IP.

## Step 3: Accessing the application

Once the app starts, navigate to `http://[public_ip_address_of_yourVM]:8501` in your web
browser to start interacting with your chatbot.

Streamlit takes a minute or two to come up after the instance reports as running. If it
does not appear, SSH in and check the bootstrap log:

```
ssh -i [YourKey.pem] ubuntu@[public_ip]
sudo cat /var/log/chatbot-lab.log
```

## Step 4: Clean up (do not skip)

```
cd Part1
python3 delete-vector-db.py --collection_name [Name_of_collection]
python3 delete-s3.py --bucket_name [YourBucketName]
```

Then terminate the EC2 instance from the console. The OpenSearch Serverless collection is
the expensive item -- it keeps billing until it is deleted.
