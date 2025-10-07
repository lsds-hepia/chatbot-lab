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

- Go to the **AWS Lambda Console**.
- Create a new function:
  - **Runtime:** Python 3.13
  - **Architecture:** arm64
- Name it something like: `vectorize-documents-groupNUMBER`.

**Why this matters:**
Lambda is AWS's **serverless compute service** - you write code without managing servers. Choosing the right runtime (Python 3.13) and architecture (arm64) is important because they must match your code dependencies.


---

### 2. Add the Function Code

Copy the provided `lambda_function.py` code into the inline editor, Save and Deploy.

This code will:
- Download the uploaded PDF from S3 into `/tmp`.
- Extract and chunk the text.
- Generate embeddings with Bedrock.
- Store them in OpenSearch.


### 3. Configure Environment Variables

Add the following environment variables in the Lambda function settings:
- `ENDPOINT` → The OpenSearch endpoint (from the first exercise).
- `INDEXNAME` → The name of the OpenSearch index (already exists or needs to be created).


---

### 4. Attach IAM Role & Policies

The Lambda function needs permissions to access other AWS services.
Attach an IAM role with these policies:
- **AmazonS3ReadOnlyAccess** → to read documents from S3.
- **AmazonBedrockFullAccess** → to use embedding models from Bedrock.
- **aws-opensearch-serverless** (a custom policy) → to store embeddings in OpenSearch.

---

### 5. Configure OpenSearch Access

- Go to your OpenSearch collection.
- In 'Data access', click on 'Associated Policy', Edit
- Under 'Rule1', add a principal to allow the **IAM role ARN** of your Lambda function to write data.

---

### 6. Configure Function Settings

In the **General Configuration** tab of your Lambda function, make the following changes:

- **Timeout:** set to **15 minutes** (the maximum allowed).
- **Ephemeral storage (/tmp):** set to the maximum **10 GB** to handle large documents.
- **Memory:** set to the maximum **10 GB**.


---

### 7. Add the Dependencies Layer

This Lambda function requires external Python libraries (`langchain`, `opensearch-py`, etc.).
- A prebuilt **Lambda Layer**, named 'vectorize-dep', has already been created for you (arm64 / Python 3.13).
- Simply attach this layer to your function under **Layers**.
- It contains all the required dependencies packaged with the same runtime and architecture as your Lambda function.

---

### 8. Configure the Trigger

- In the Lambda **Triggers** section, add:
  - **S3 bucket** → select the provided bucket.
  - **Event type:** `PUT` (ObjectCreated) → so the function runs when a file is uploaded.


---

### 9. Test the Setup

1. Upload a PDF into the assigned S3 bucket.
2. Check the Monitor tab to confirm that the function was triggered.
3. Verify that embeddings were added to the OpenSearch index.


