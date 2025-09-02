# Creator: Abir Chebbi (abir.chebbi@hesge.ch)

import boto3
import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain_community.vectorstores import OpenSearchVectorSearch
import argparse

## S3_client
s3_client = boto3.client('s3')

## Bedrock client - use the same region as configured
session = boto3.Session()
region = session.region_name or 'us-east-1'  # fallback to us-east-1 if region not configured
bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=region)


## Configuration for AWS authentication and OpenSearch client
credentials = session.get_credentials()
awsauth = AWSV4SignerAuth(credentials, region, 'aoss')
## Embedding model IDs 
model_ids = [
        "amazon.titan-embed-text-v2:0",    # Latest version
        "amazon.titan-embed-text-v1",      # Previous version
        "cohere.embed-english-v3"          # Alternative
    ]

## Create Index in Opensearch
def create_index(client,index_name):
    indexBody = {
        "settings": {
            "index.knn": True
        },
        "mappings": {
            "properties": {
                "vector_field": {
                    "type": "knn_vector",
                    "dimension": 1024,  # Updated to match actual embedding dimension
                    "method": {
                        "engine": "faiss",
                        "name": "hnsw"
                    }
                }
            }
        }
    }

    try:
        create_response = client.indices.create(index_name, body=indexBody)
        print('\nCreating index:')
        print(create_response)
    except Exception as e:
        print(e)
        print("(Index likely already exists?)") 



## Load docs from S3
def download_documents(bucket_name,local_dir):
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    for item in response['Contents']:
            key = item['Key']
            if key.endswith('.pdf'):
                local_filename = os.path.join(local_dir, key)
                s3_client.download_file(Bucket=bucket_name, Key=key, Filename=local_filename)

   
    



## Split pages/text into chunks
def split_text(docs, chunk_size, chunk_overlap):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_documents(docs)   

    return chunks
 
## Generate embeddings 
def generate_embeddings(bedrock_client, chunks):
    
    embeddings_model = None
    for model_id in model_ids:
        try:
            embeddings_model = BedrockEmbeddings(model_id=model_id, client=bedrock_client)
            print(f"Using embedding model: {model_id}")
            break
        except Exception as e:
            print(f"Model {model_id} not available: {e}")
            continue
    
    if embeddings_model is None:
        raise ValueError("No embedding model available. Please check your Bedrock model access.")
    
    chunks_list=[chunk.page_content for chunk in chunks]
    embeddings = embeddings_model.embed_documents(chunks_list)
    
    # Debug: Print actual embedding dimensions
    if embeddings:
        actual_dimension = len(embeddings[0])
        print(f"Actual embedding dimension: {actual_dimension}")
        if actual_dimension != 1024:
            print(f"WARNING: Embedding dimension ({actual_dimension}) doesn't match index dimension (1024)")
    
    return embeddings

# Store generated embeddings into an OpenSearch index.
def store_embeddings(embeddings, texts, meta_data, host, awsauth, index_name):  
    
    docsearch = OpenSearchVectorSearch.from_embeddings(
        embeddings,
        texts,
        meta_data,
        opensearch_url=f'https://{host}:443',
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        index_name=index_name,
        bulk_size=100,  # Reduced bulk size to avoid timeouts
        timeout=120,    # Increased timeout to 2 minutes
        max_chunk_bytes=10485760  # 10MB max chunk size
)

    return docsearch


# Func to do both generating and storing embeddings
def generate_store_embeddings(bedrock_client, chunks, host, awsauth, index_name):
   
    embeddings_model = None
    for model_id in model_ids:
        try:
            embeddings_model = BedrockEmbeddings(model_id=model_id, client=bedrock_client)
            print(f"Using embedding model: {model_id}")
            break
        except Exception as e:
            print(f"Model {model_id} not available: {e}")
            continue
    
    if embeddings_model is None:
        raise ValueError("No embedding model available. Please check your Bedrock model access.")
    
    docsearch = OpenSearchVectorSearch.from_documents(
        chunks,
        embeddings_model,
        opensearch_url=f'https://{host}:443',
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        index_name=index_name,
        bulk_size=100,  # Reduced bulk size to avoid timeouts
        timeout=120,    # Increased timeout to 2 minutes
        max_chunk_bytes=10485760  # 10MB max chunk size
)

    return docsearch



## main 
def main(bucket_name, endpoint,index_name, local_path):

    ## Opensearch Client
    OpenSearch_client = OpenSearch(
        hosts=[{'host': endpoint, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=120,    # 2 minute timeout
        max_retries=3,  # Retry failed requests
        retry_on_timeout=True
    )

    download_documents(bucket_name,local_path)
    loader= PyPDFDirectoryLoader(local_path)
    docs = loader.load()
    print('Start chunking')
    chunks = split_text(docs, 1000, 100)
    print(chunks[1])
    create_index(OpenSearch_client,index_name)
    print('Start vectorising')
    embeddings= generate_embeddings(bedrock_client, chunks)
    print(embeddings[1])
    texts = [chunk.page_content for chunk in chunks]
     # Prepare metadata for each chunk
    meta_data = [{'source': chunk.metadata['source'], 'page': chunk.metadata['page'] + 1} for chunk in chunks]
    print('Start storing')
    print(f"Storing {len(embeddings)} embeddings in batches...")
    
    try:
        store_embeddings(embeddings, texts, meta_data, endpoint, awsauth, index_name)
        print('End storing - Success!')
    except Exception as e:
        print(f"Error storing embeddings: {e}")
        print("You may need to:")
        print("1. Check your OpenSearch cluster is active and accessible")
        print("2. Verify your network policies allow access")
        print("3. Try reducing the batch size further")
        raise


if __name__== "__main__":
    parser = argparse.ArgumentParser(description="Process PDF documents and store their embeddings.")
    parser.add_argument("--bucket_name", help="The S3 bucket name where documents are stored")
    parser.add_argument("--endpoint", help="The OpenSearch service endpoint")
    parser.add_argument("--index_name", help="The name of the OpenSearch index")
    parser.add_argument("--local_path", help="local path")
    args = parser.parse_args()
    main(args.bucket_name, args.endpoint, args.index_name, args.local_path)
