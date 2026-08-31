# chatbot lab

Build a RAG chatbot on AWS: store lecture PDFs in **S3**, embed them with **Bedrock**,
index the vectors in **OpenSearch Serverless**, and serve a **Streamlit** chat UI from **EC2**.

## Set up environment:
1. Use your credentials to create an Ubuntu 24.04 specific VM on the AWS Amazon portal
2. **Install and configure the AWS CLI** on the VM you just created (refer to the setup
   guide provided in Session 1). Then configure it with your credentials:

    ```
    aws configure
    ```

   It asks for four values:

    ```
    AWS Access Key ID     : [your access key]
    AWS Secret Access Key : [your secret key]
    Default region name   : us-east-1
    Default output format : json
    ```

3. Ensure python is installed: **python 3.10 or higher** (required by langchain-core 1.x, langchain-aws, streamlit and boto3). Ubuntu 24.04 ships 3.12, so the stock VM is fine.

4. **Create a virtual environment.** Ubuntu 24.04 refuses system-wide `pip install`
   (`error: externally-managed-environment`), so all the Python steps below run inside a venv:

    ```
    sudo apt update && sudo apt install -y python3-venv
    python3 -m venv ~/chatbotlab
    source ~/chatbotlab/bin/activate
    ```

   Re-run `source ~/chatbotlab/bin/activate` in every new SSH session. Once it is active,
   `pip3` and `python3` refer to the venv.

   You do **not** need to run `aws configure` again inside the venv. Credentials live in
   `~/.aws/credentials`, outside the environment, so boto3 finds them from anywhere. Check
   with:

    ```
    aws sts get-caller-identity
    ```

   This prints your account ID and IAM user ARN -- both are needed in Part 1 Step 2. If it
   fails, your AWS CLI is not configured yet.

   **Use the same region everywhere.** Every script takes `--region` and defaults to
   `us-east-1`. If your course uses a different region, pass `--region` to *all* of them.

5. **Install Docker** (used in Part 3):

    ```
    sudo apt update && sudo apt install -y docker.io
    sudo usermod -aG docker $USER
    ```

   Log out and back in so the group change takes effect, then check it works:

    ```
    docker --version
    docker run --rm hello-world
    ```

   On macOS, install Docker Desktop instead and make sure it is running.

## Part 1:

Go to the Part1 folder: `cd Part1`

With the virtual environment active, install the required python libraries:
`pip3 install -r requirements.txt`

### Step 1: Object storage Creation

Create an S3 bucket and upload a few PDF files by running:

`python3 create-S3-and-put-docs.py --bucket_name [YourBucketName] --local_path [PathToYourPDFFiles]`

Where placeholders:
- **[YourBucketName]**: The name for the new S3 bucket to be created.
- **[PathToYourPDFFiles]**: the folder on your machine that **already contains** the PDF
  files you want to upload. Only files ending in `.pdf` are uploaded.

Optional: `--region` (default `us-east-1`).

### Step 2: Vector Store Creation

Create a vector database for storing embeddings by running:

`python3 create-vector-db.py --collection_name [Name_of_collection] --task_role_arn [TaskRoleArn]`

Where:
- **[Name_of_collection]**: Name of the collection that you want to create.
- **[TaskRoleArn]**: the identifier of the role your instructor created, for example
  `arn:aws:iam::[YourAccount_ID]:role/chatbot-lab-task-role`.

**What is a role, and why does the database need to know about it?**

A new collection is private: only the identity that created it can read or write. Right now
that is *you*, using the keys `aws configure` stored on your machine, and that is what
Step 3 needs to load the embeddings.

But in Parts 2 and 3 the chatbot does not run on your machine and cannot use your keys. It
runs on a server, and a server is given an **IAM role** instead: a set of permissions with
no password and no keys, that AWS lends to a machine for a few hours at a time. An **ARN**
(*Amazon Resource Name*) is simply the full identifier of an AWS resource -- here, of that
role.

Optional: `--region` (default `us-east-1`).

The script performs the following actions:

* Sets up encryption, network, and data access policies for the collection.
* Creates a vector store with the name collection entered as argument.
* Waits for the collection to become ACTIVE, then displays the store's endpoint.

**Copy the endpoint it prints** -- you need it in Step 3 and in Part 2.

### Step 3: Vectorizing the PDF Files:

After setting up the S3 bucket and Vector DB, we process the PDF files to generate and
store embeddings in the vector database.

This is the first step that calls Bedrock, so you need the ID of an **embedding model**.
Open **Bedrock > Model catalog** in your region and find one, for example
`amazon.titan-embed-text-v2:0`.

Model availability differs between regions. You can list what your account can actually
use from the command line:

```
aws bedrock list-foundation-models --region us-east-1 \
  --query "modelSummaries[?outputModalities[0]=='EMBEDDING'].modelId" --output text
```

`amazon.titan-embed-text-v2:0` is the cheapest of the general-purpose embedding models and
is the default used here. It produces 1024-dimensional vectors.

Then run:

`python3 vectorise-store.py --bucket_name [YourBucketName] --endpoint [YourVectorDBEndpoint] --index_name [Index_name]`

Where:

- **[YourBucketName]**: The name of the S3 bucket containing the PDF files.
- **[YourVectorDBEndpoint]**: Endpoint of the vector database (without `https://`).
- **[Index_name]**: The index_name where to store the embeddings in the collection.

Optional: `--region`, `--embed_model_id`, and `--download_path`.

The vectorise-store.py script will:

* Download PDF files from the S3 bucket.
* Split them into chunks.
* Generate embeddings from the chunks.
* Create an index in the vector DB, sized to match your embedding model.
* Store these embeddings in the OpenSearch Vector DB.

## Part 2:

### Step 1: Preparation

Go to the Part2 folder: `cd Part2`

With the virtual environment active, install the required python libraries:
`pip3 install -r requirements.txt`

Before deploying the chatbot on an EC2 instance, complete the following preliminary steps:

1. **Create a Key Pair**: This key pair will be used for SSH access to your EC2 instance.

2. **Create a Security Group**: Define rules to allow the instance to be accessible externally. The security group should include the following rules:
    - For inbound rules: you need to allow SSH traffic, HTTP/HTTPs traffic and open port 8501 used by the application.
    - Outbound Rules: Allow all traffic.

3. **Create the config file**: copy `config.ini.example` to `config.ini` and fill it in:

    ```ini
    [aws]
    region = us-east-1

    [opensearch]
    endpoint = YOUR_OPENSEARCH_ENDPOINT
    index_name = YOUR_INDEX_NAME

    [bedrock]
    embed_model_id = amazon.titan-embed-text-v2:0
    chat_model_id = us.anthropic.claude-haiku-4-5-20251001-v1:0
    ```

   `config.ini` is gitignored. Never commit it.

   `endpoint` and `index_name` are the values from Part 1.

   For `chat_model_id` the lab uses **Claude Haiku 4.5**, the cheapest current-generation
   Claude model. Note the `us.` prefix:

    ```
    us.anthropic.claude-haiku-4-5-20251001-v1:0
    ```

### Step 2: Launching the Instance

`create_instance.py` starts an instance and sends it everything it needs to run the
chatbot: your `chatbot.py`, your `requirements.txt` and your `config.ini` all travel with
the instance as its **user data**, the script EC2 runs once at first boot.

Run:

`python3 create_instance.py --key_pair_name [KeyPairName] --security_group_id [SecurityGroupID] --instance_profile [InstanceProfile]`

Where:

- **[KeyPairName]**: The name of the key_pair created earlier.
- **[SecurityGroupID]**: The id of the security group created earlier.
- **[InstanceProfile]**: the instance profile your instructor created `chatbot-lab-task-role`.  It gives the instance permission to call Bedrock and OpenSearch.

Optional: `--instance_type` (default `t3.micro`), `--region`, and `--ami_id`.

There is no image to prepare. The script looks up the latest official Ubuntu 24.04 image
and prints which one it chose, then the instance installs Python, creates a virtualenv,
installs the requirements and starts Streamlit. Everything it does is written to
`/var/log/chatbot-lab.log`.

The script waits for the instance to start and prints its public IP.

### Step 3: Accessing the application

Once the app starts, navigate to `http://[public_ip_address_of_yourVM]:8501` in your web
browser to start interacting with your chatbot.

Streamlit takes a minute or two to come up after the instance reports as running. If it
does not appear, SSH in and check the bootstrap log:

```
ssh -i [YourKey.pem] ubuntu@[public_ip]
sudo cat /var/log/chatbot-lab.log
```

### Step 4: Stop the instance

Terminate the EC2 instance from the console when you are done with Part 2. Do not delete
the S3 bucket or the vector DB yet -- Part 3 reuses them.

## Part 3: Containerizing the chatbot

In Part 2 you deployed the application by putting it on a server you had to create,
configure and connect to. In Part 3 you deploy exactly the same application as a
**container image**, and let AWS run it for you.

### What you will learn

- How an image registry (Amazon ECR) stores versioned, immutable artifacts
- How configuration is injected at run time instead of being baked into the image
- What a managed container service creates on your behalf, and what it costs
- What a request passes through before it reaches your container

### Prerequisites

Check that Docker is installed and running (step 5 of *Set up environment*):

```
docker --version
```

You also need the S3 bucket, the vector DB and the index from Part 1. The chatbot is the
same; only the way it is packaged and deployed changes.

### Step 1: Build the image

```
cd Part3
docker build --platform linux/amd64 --provenance=false -t chatbot-lab .
```

`--platform linux/amd64` is required. AWS Fargate runs `X86_64`, so an image built on an
Apple Silicon Mac (arm64) starts and immediately dies with `exec format error`.

The image contains the application and its dependencies, and nothing else: no endpoint, no
index name, no credentials. Compare `Part3/chatbot.py` with `Part2/chatbot.py`:

```
diff ../Part2/chatbot.py chatbot.py
```

Part 2 reads `config.ini`; Part 3 reads environment variables, which you will set on the
service in Step 3. **Why can the image not simply contain `config.ini`?** Because an image
is a shared artifact: it is pushed to a registry, and anyone who can pull it can read every
layer inside it. `env.example` lists the variables the container expects.

### Step 2: Push the image to Amazon ECR

The image has to live in Amazon ECR, following these steps:

**1. Create the repository.** One repository holds all the versions of one application.
Unlike an S3 bucket, the name only has to be unique inside your own account and region.

```
aws ecr create-repository --repository-name [Repo] --region [REGION]
```

Where:

- **[Repo]**: the name of the repository to create, for example `chatbot-lab-[GroupNumber]`.
- **[REGION]**: the AWS region, `us-east-1` for this lab.

The output contains a **`repositoryUri`**: the address of your repository, which the next
three commands need. It has the form:

```
[YourAccount_ID].dkr.ecr.[REGION].amazonaws.com/[Repo]
```

Where:

- **[YourAccount_ID]**: your 12-digit AWS account number. Print it with
  `aws sts get-caller-identity --query Account --output text`.
- **[RegistryAddress]**: everything before the repository name, that is
  `[YourAccount_ID].dkr.ecr.[REGION].amazonaws.com`. You log in to this address, and you
  tag and push to `[RegistryAddress]/[Repo]`.

**2. Log Docker in to the registry.** ECR is private, so Docker has to authenticate.

```
aws ecr get-login-password --region [REGION] \
  | docker login --username AWS --password-stdin [RegistryAddress]
```

`get-login-password` exchanges your AWS credentials for a temporary token, valid 12 hours,
and the pipe hands it straight to Docker. `--password-stdin` reads it from the pipe rather
than the command line.

You should see `Login Succeeded`.

**3. Tag the image with its destination.**

```
docker tag chatbot-lab:latest [RegistryAddress]/[Repo]:v1
```

This copies nothing. It gives the image you already built a second name meaning "this
belongs in that repository, as version `v1`".

**4. Upload it.**

```
docker push [RegistryAddress]/[Repo]:v1
```

`--provenance=false` in the build keeps ECR to one image per push. Without it Docker
also pushes a build-metadata attestation and an index, which show up as extra untagged
rows.

### Step 3: Deploy with ECS Express Mode

1. Open the ECS console and choose **Express mode** in the navigation pane.
2. For **Image URI**, choose **Browse ECR images** and select your `v1` image.
3. Leave **Task execution role** and **Infrastructure role** as they are.

4. Open **Additional configurations** and set:
   - **Container port**: `8501` (the default is 80; Streamlit does not listen there)
   - **Health check path**: `/_stcore/health` (Streamlit's health endpoint)
   - **Environment variables**: `AWS_REGION`, `OPENSEARCH_ENDPOINT`, `OPENSEARCH_INDEX`,
     `BEDROCK_CHAT_MODEL_ID`
   - **Task role**: choose **`chatbot-lab-task-role`** from the list. This role is what gives the container permission to call Bedrock and OpenSearch.

5. Choose **Create**, then open the **Application URL** when the deployment finishes.

You gave AWS an image and four settings. Note that the URL is **HTTPS** -- you did not
request a certificate or configure a load balancer.

### Step 4: Find out what AWS actually built

Express Mode made deployment easy by hiding the infrastructure. Go and find it. Everything
it created lives in your own account. Locate each of the following in the console and write
down its name:

| Resource | Where to look |
|---|---|
| ECS cluster | ECS > Clusters |
| Task definition (CPU, memory, env vars) | ECS > Task definitions |
| Application Load Balancer | EC2 > Load Balancers |
| Target group and its health checks | EC2 > Target Groups |
| Security groups (service and load balancer) | EC2 > Security Groups |
| Auto scaling policy | ECS > your service > Health and metrics |
| CloudWatch log group | CloudWatch > Log groups |
| TLS certificate | AWS Certificate Manager |

**Draw the architecture** from what you found: where does a request from your browser go,
and what does it pass through before reaching the container? Compare that drawing with
Part 2, where a request went straight to a public IP on port 8501.

### Step 5: Compare the two deployments

Fill this in from your own experience of Parts 2 and 3:

| | Part 2 (EC2) | Part 3 (container) |
|---|---|---|
| What you had to create by hand | | |
| Where the app's dependencies are defined | | |
| How you deploy a change | | |
| Is it reachable over HTTPS? | | |
| What you pay for when nobody is using it | | |

For the last row: Fargate bills for vCPU and memory per second while a task runs, and the
load balancer bills continuously. Work out roughly what your service costs per month if you
leave it running, and compare that with a `t3.micro`. Then answer: **can this service scale
to zero, and what would happen to a request that arrived while it was at zero?**

## Clean up (do not skip)

Delete everything in this order:

```
cd Part1
python3 delete-vector-db.py --collection_name [Name_of_collection]
python3 delete-s3.py --bucket_name [YourBucketName]
```

Then, in the console:

- Delete the **ECS Express Mode service** (this also removes the load balancer, target
  group, certificate and scaling policy it created)
- Delete the **ECR repository** holding your images
- Terminate the **EC2 instance** from Part 2 if it is still running

Check the console afterwards and confirm that no collection and no load balancer remain.
