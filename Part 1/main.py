import boto3
import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import BedrockEmbeddings
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain_community.vectorstores import OpenSearchVectorSearch

##  Local directory for storing PDF files
LOCAL_DIR = "pdfs" 
index_name = "cloud_lecture_test"


## S3_client
s3_client = boto3.client('s3')
## Bucket name where documents are stored
BUCKET_NAME = "chatbotlab"

## Bedrock client
bedrock_client = boto3.client(service_name="bedrock-runtime")


## Configuration for AWS authentication and OpenSearch client
credentials = boto3.Session().get_credentials()
awsauth = AWSV4SignerAuth(credentials, 'us-east-1', 'aoss')

## Vector DB endpoint
host= 'd7gvxdj7jpz3h3bj0xq6.us-east-1.aoss.amazonaws.com'

## Opensearch Client
OpenSearch_client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
    
)

## Create Index in Opensearch
def create_index(index_name):
    indexBody = {
        "settings": {
            "index.knn": True
        },
        "mappings": {
            "properties": {
                "vector_field": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {
                        "engine": "faiss",
                        "name": "hnsw"
                    }
                }
            }
        }
    }

    try:
        create_response = OpenSearch_client.indices.create(index_name, body=indexBody)
        print('\nCreating index:')
        print(create_response)
    except Exception as e:
        print(e)
        print("(Index likely already exists?)") 



## Load docs from S3
def load_docs(bucket_name,local_dir):
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    for item in response['Contents']:
            key = item['Key']
            if key.endswith('.pdf'):
                local_filename = os.path.join(local_dir, key)
                s3_client.download_file(Bucket=bucket_name, Key=key, Filename=local_filename)

   
    



## Split pages/text into chunks
def split_text(pages, chunk_size, chunk_overlap, local_dir):
    loader= PyPDFDirectoryLoader(local_dir)
    pages = loader.load_and_split()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_documents(pages)   
    return chunks
 
## Generate embeddings and index them using Opensearch

def generate_embeddings(bedrock_client, chunks,awsauth,index_name):
    embeddings_model = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=bedrock_client)
    docsearch = OpenSearchVectorSearch.from_documents(
        chunks,
        embeddings_model,
        opensearch_url=f'https://{host}:443',
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        index_name=index_name,
        bulk_size=1000
)

    return docsearch



## main 
def main():

    docs= load_docs(BUCKET_NAME,LOCAL_DIR)
    chunks=split_text(docs, 1000, 100, LOCAL_DIR)
    print("Sample chunk:", chunks[0])
    create_index(index_name)
    embeddings = generate_embeddings(bedrock_client, chunks,awsauth,index_name)
    print("Embeddings processing completed", embeddings)


  




if __name__== "__main__":
    main()
