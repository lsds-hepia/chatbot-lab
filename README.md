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
    Default region name   : eu-central-1
    Default output format : json
    ```

   **This lab uses `eu-central-1` (Frankfurt).** Every script defaults to that region. Use
   the same region here, in `config.ini` and in the Part 3 commands -- the S3 bucket, the
   vector database and the Bedrock calls must all be in one region or they cannot see each
   other.
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
   `eu-central-1`. If your course uses a different region, pass `--region` to *all* of them.

## Part 1:

Go to the Part1 folder: `cd Part1`

With the virtual environment active, install the required python libraries:
`pip3 install -r requirements.txt`

### Step 1: Object storage Creation

Create an S3 bucket and upload a few PDF files by running:

`python3 create-S3-and-put-docs.py --bucket_name [YourBucketName] --local_path [PathToYourPDFFiles]`

Where placeholders:
- **[YourBucketName]**: The name for the new S3 bucket to be created.
- **[PathToYourPDFFiles]**: The local directory path where the PDF files are stored.

Optional: `--region` (default `eu-central-1`).

### Step 2: Vector Store Creation

Create a vector database for storing embeddings by running:

`python3 create-vector-db.py --collection_name [Name_of_collection] --iam_user [YourIAM_user] --account_id [YourAccount_ID]`

Where:
- **[Name_of_collection]**: Name of the collection that you want to create.
- **[YourIAM_user]** : the IAM user of your account.
- **[YourAccount_ID]** : the ACCOUNT ID of your account.

Optional: `--region` (default `eu-central-1`).

You will find YourIAM_user and YourAccount_ID when you click on your account ID in the top
right-hand corner of the AWS Amazon portal, or by running `aws sts get-caller-identity`.

The script performs the following actions:

* Sets up encryption, network, and data access policies for the collection.
* Creates a vector store with the name collection entered as argument.
* Waits for the collection to become ACTIVE, then displays the store's endpoint.

**Copy the endpoint it prints** -- you need it in Step 3 and in Part 2.

### Step 3: Vectorizing the PDF Files:

After setting up the S3 bucket and Vector DB, we process the PDF files to generate and
store embeddings in the vector database.

This is the first step that calls Bedrock, so you need an **embedding model** enabled.
Open **Bedrock > Model access** in your region and check that an embedding model such as
`amazon.titan-embed-text-v2:0` is granted; request access if it is not.

Model availability differs between regions, so **copy the exact model ID from the console**
rather than assuming the default below exists in yours. In European regions many models are
offered only as cross-region inference profiles, whose IDs carry an `eu.` prefix (for
example `eu.anthropic.…` instead of `anthropic.…`). If the console shows an ID starting
with `eu.`, use it exactly as shown.

Then run:

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
    region = eu-central-1
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

   For `chat_model_id` you need a **Claude** model enabled in **Bedrock > Model access**.
   Copy the exact model ID from the console -- it is region-specific. `endpoint` and
   `index_name` are the values from Part 1.

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

- How a `Dockerfile` describes an application and all of its dependencies
- How an image registry (Amazon ECR) stores versioned, immutable artifacts
- How configuration is injected at run time instead of being baked into the image
- What a managed container service creates on your behalf, and what it costs
- How to operate an application you cannot SSH into

### Prerequisites

You need Docker installed on your machine (or on the VM from Part 1):

```
docker --version
```

If it is not installed on the Ubuntu VM:

```
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker $USER
```

Log out and back in so the group change takes effect, then check `docker --version` again.

You also need the S3 bucket, the vector DB and the index from Part 1. The chatbot is the
same; only the way it is packaged and deployed changes.

> **Instructor note:** an ECS Express Mode service needs a **task execution role** and an
> **infrastructure role** (AWS managed policies `AmazonECSTaskExecutionRolePolicy` and
> `AmazonECSInfrastructureRoleforExpressGatewayServices`). The console offers to create
> them, which requires IAM permissions. If student accounts cannot create IAM roles, create
> both roles once beforehand and give students the names, along with `iam:PassRole` on them.

### Step 1: Read the Dockerfile

Open `Part3/Dockerfile` before building anything. Note two things:

1. `requirements.txt` is copied and installed **before** `chatbot.py` is copied. Docker
   caches each instruction as a layer, so editing the application code does not re-run the
   slow `pip install`. You will verify this in Step 3.
2. Nothing in the image contains your endpoint, your index name or your AWS keys. Compare
   `Part3/chatbot.py` with `Part2/chatbot.py`:

   ```
   diff Part2/chatbot.py Part3/chatbot.py
   ```

   Part 2 reads `config.ini`. Part 3 reads environment variables. **Why can a container
   image not contain config.ini?** Because the image is a shared, immutable artifact -- it
   gets pushed to a registry, and anyone who can pull it can read every layer inside it.

### Step 2: Build and run the image locally

```
cd Part3
docker build --platform linux/amd64 -t chatbot-lab .
```

> `--platform linux/amd64` is required. AWS Fargate runs `X86_64` by default, so an image
> built on an Apple Silicon Mac (arm64) will start and immediately die with
> `exec format error`. This is one of the most common container deployment mistakes.

Run it locally, passing the configuration as environment variables:

```
docker run -p 8501:8501 \
  -e AWS_REGION=eu-central-1 \
  -e AWS_ACCESS_KEY_ID=[YourKeyId] \
  -e AWS_SECRET_ACCESS_KEY=[YourSecret] \
  -e OPENSEARCH_ENDPOINT=[YourVectorDBEndpoint] \
  -e OPENSEARCH_INDEX=[Index_name] \
  -e BEDROCK_CHAT_MODEL_ID=[YourChatModelId] \
  chatbot-lab
```

Open `http://localhost:8501`. The same application you deployed on a VM in Part 2 now runs
in a container on your own machine, with no virtualenv and no installation steps.

### Step 3: Watch the layer cache

Add a blank line to `Part3/chatbot.py`, then build again:

```
docker build --platform linux/amd64 -t chatbot-lab .
```

Look at the output: the `pip install` step says `CACHED` and the build finishes in
seconds. Now move the `COPY chatbot.py .` line **above** the `COPY requirements.txt .`
line and rebuild. What happens, and why? Put the Dockerfile back when you are done.

### Step 4: Push the image to Amazon ECR

An image on your laptop is not deployable. Push it to a registry.

```
aws ecr create-repository --repository-name chatbot-lab-[YourName] --region eu-central-1

aws ecr get-login-password --region eu-central-1 \
  | docker login --username AWS --password-stdin [YourAccount_ID].dkr.ecr.eu-central-1.amazonaws.com

docker tag chatbot-lab:latest [YourAccount_ID].dkr.ecr.eu-central-1.amazonaws.com/chatbot-lab-[YourName]:v1
docker push [YourAccount_ID].dkr.ecr.eu-central-1.amazonaws.com/chatbot-lab-[YourName]:v1
```

Note the tag `v1`. You are going to push a `v2` later. **Tags are how you version and roll
back a deployment** -- there is no equivalent to this in the Part 2 workflow.

### Step 5: Deploy with ECS Express Mode

1. Open the ECS console and choose **Express mode** in the navigation pane.
2. For **Image URI**, choose **Browse ECR images** and select your `v1` image.
3. Choose the **Task execution role** and **Infrastructure role**.
4. Open **Additional configurations** and set:
   - **Container port**: `8501` (the default is 80; Streamlit does not listen there)
   - **Health check path**: `/_stcore/health` (Streamlit's health endpoint)
   - **Environment variables**: `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
     `OPENSEARCH_ENDPOINT`, `OPENSEARCH_INDEX`, `BEDROCK_CHAT_MODEL_ID`
5. Choose **Create**, then open the **Application URL** when the deployment finishes.

You gave AWS an image and six settings. Note that the URL is **HTTPS** -- you did not
request a certificate or configure a load balancer.

> **Discussion:** you have just typed your secret key into a form. The **Value type** field
> next to each environment variable offers **Secret** instead of **Environment variable**,
> which reads the value from AWS Secrets Manager at start-up. Why is that better? Who can
> read a task definition?

### Step 6: Find out what AWS actually built

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

### Step 7: Operate it without SSH

There is no SSH into a Fargate task. Open **CloudWatch > Log groups** and find your
service's log group. This is where `print()` output and Streamlit's own logs now go.

Now break it on purpose:

1. Edit the `BEDROCK_CHAT_MODEL_ID` environment variable to an invalid value and update
   the service.
2. Ask the chatbot a question.
3. Find the error in CloudWatch and identify the cause **without** connecting to any server.

Then set it back.

### Step 8: Scaling, and a problem to discover

In the ECS console, set the **minimum number of tasks** to 2 and update the service.

Once two tasks are running, open the application URL, ask a question, then open the same
URL in a private browser window and ask another. Compare the chat histories.

**What happened, and why?** The AWS documentation describes Express Mode as being for
*stateless* applications. Look at `chatbot.py`: `st.session_state.chat_history` lives in
the memory of one task. The load balancer sends your two browser sessions to different
tasks, and neither knows about the other's conversation.

Discuss: what would you have to change to run this application on more than one task?
Where should the chat history live instead?

Set the minimum back to 1 when you are done.

### Step 9: Ship a new version

Change the title in `Part3/chatbot.py`, then build, tag as `v2` and push:

```
docker build --platform linux/amd64 -t chatbot-lab .
docker tag chatbot-lab:latest [YourAccount_ID].dkr.ecr.eu-central-1.amazonaws.com/chatbot-lab-[YourName]:v2
docker push [YourAccount_ID].dkr.ecr.eu-central-1.amazonaws.com/chatbot-lab-[YourName]:v2
```

Update the service to point at `v2` and watch the deployment. The old container is replaced
by a new one; nothing is patched in place. Then point it back at `v1` -- you have just
rolled back a release.

### Step 10: Compare the two deployments

Fill this in from your own experience of Parts 2 and 3:

| | Part 2 (EC2) | Part 3 (container) |
|---|---|---|
| What you had to create by hand | | |
| Where the app's dependencies are defined | | |
| How you deploy a change | | |
| How you read the logs | | |
| What happens if the app crashes | | |
| How you run a second copy | | |
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

> ### Cost warning
> An **OpenSearch Serverless collection bills continuously** for a minimum number of
> OCU-hours, whether or not you are querying it, and an Application Load Balancer bills by
> the hour even with no traffic. These two are the expensive items in this lab -- deleting
> the S3 bucket and terminating the EC2 instance is not enough on its own.

Check the console afterwards and confirm that no collection and no load balancer remain.
