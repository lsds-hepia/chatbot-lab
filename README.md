# Exercise: Build an AWS Lambda Function for Document Vectorization

## 🎯 Objective
In this exercise, you will create an **AWS Lambda function** that:
1. Is triggered when a document is uploaded to an existing S3 bucket.
2. Extracts and splits the text into chunks.
3. Generates embeddings using **Amazon Bedrock**.
4. Stores the embeddings in an **OpenSearch vector database**.

We will use the S3 bucket and OpenSearch vector database already created in the first exercise. Your job is to create and configure the Lambda function.


---

## 📝 Steps

### 1. Create the Lambda Function
**What to do:**
- Go to the **AWS Lambda Console**.
- Create a new function:
  - **Runtime:** Python 3.13
  - **Architecture:** arm64
- Name it something like: `vectorize-documents-groupNUMBER`.

**Why this matters:**
Lambda is AWS's **serverless compute service** - you write code without managing servers. Choosing the right runtime (Python 3.13) and architecture (arm64) is important because:

- Runtime version and architecture must match your code dependencies
- Understanding serverless means you only pay for actual execution time, not idle server hours

---

### 2. Add the Function Code
**What to do:**
Copy the provided `lambda_function.py` code into the inline editor, Save and Deploy.

This code will:
- Download the uploaded PDF from S3 into `/tmp`.
- Extract and chunk the text.
- Generate embeddings with Bedrock.
- Store them in OpenSearch.


### 3. Configure Environment Variables
**What to do:**
Add the following environment variables in the Lambda function settings:
- `ENDPOINT` → The OpenSearch endpoint (from the first exercise).
- `INDEXNAME` → The name of the OpenSearch index (already exists or needs to be created).

**Why this matters:**
Environment variables are a **best practice for cloud configuration management** because:
- **Separation of code and config**: Same code works across dev/staging/production
- **Security**: Sensitive endpoints aren't hardcoded in source code
- **Flexibility**: Easy to update configuration without redeploying code
- This follows the **12-factor app methodology**, essential for cloud-native applications

---

### 4. Attach IAM Role & Policies
**What to do:**
The Lambda function needs permissions to access other AWS services.
Attach an IAM role with at least these policies:
- **AmazonS3ReadOnlyAccess** → to read documents from S3.
- **AmazonBedrockFullAccess** → to use embedding models from Bedrock.
- **aws-opensearch-serverless** (a custom policy) → to store embeddings in OpenSearch.

**Why this matters:**
This demonstrates **Identity and Access Management (IAM)**, one of the most critical cloud concepts:
- **Principle of Least Privilege**: Only grant the minimum permissions needed
- **Security boundaries**: Services can't access resources without explicit permission
- IAM roles for Lambda avoid storing credentials in code (a major security risk)

---

### 5. Configure OpenSearch Access
**What to do:**
- Go to your OpenSearch collection.
- In 'Data access', click on 'Associated Policy', Edit
- Under 'Rule1', add a principal to allow the **IAM role ARN** of your Lambda function to write data.

**Why this matters:**
This shows **resource-based policies** and **bidirectional authorization**:
- IAM role grants Lambda permission to call OpenSearch (identity-based policy)
- OpenSearch policy must also allow that specific role (resource-based policy)

---

### 6. Configure Function Settings
**What to do:**
In the **General Configuration** tab of your Lambda function, make the following changes:

- **Timeout:** set to **15 minutes** (the maximum allowed).
- **Ephemeral storage (/tmp):** set to the maximum **10 GB** to handle large documents.
- **Memory:** set to the maximum **10 GB**.


---

### 7. Add the Dependencies Layer
**What to do:**
This Lambda function requires external Python libraries (`langchain`, `opensearch-py`, `pypdf`, etc.).
- A prebuilt **Lambda Layer**, named 'vectorize-dep', has already been created for you (arm64 / Python 3.13).
- Simply attach this layer to your function under **Layers**.
- It contains all the required dependencies packaged with the same runtime and architecture as your Lambda function.

**Why this matters:**
Lambda Layers demonstrate **dependency management in serverless**:
- **Separation of concerns**: Code vs. dependencies are managed separately
- **Reusability**: One layer can be shared across multiple functions
- **Size limits**: Lambda deployment packages have size limits (50 MB zipped, 250 MB unzipped) - layers help you work around this
- **Version compatibility**: Runtime and architecture must match between layer and function
- This pattern reduces deployment time and package size for your actual function code

---

### 8. Configure the Trigger
**What to do:**
- In the Lambda **Triggers** section, add:
  - **S3 bucket** → select the provided bucket.
  - **Event type:** `PUT` (ObjectCreated) → so the function runs when a file is uploaded.

**Why this matters:**
This demonstrates **event-driven architecture**, a core cloud pattern:
- **Loose coupling**: S3 doesn't know about Lambda - they communicate via events
- **Scalability**: Automatically processes any number of uploads in parallel
- **Reactive systems**: Function only runs when needed (cost-efficient)

---

### 9. Test the Setup
**What to do:**
1. Upload a PDF into the assigned S3 bucket.
2. Check the Monitor tab to confirm that the function was triggered.
3. Verify that embeddings were added to the OpenSearch index.


