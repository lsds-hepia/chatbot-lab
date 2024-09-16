# Creator: Abir Chebbi (abir.chebbi@hesge.ch)

import boto3
import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import BedrockEmbeddings
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain_community.vectorstores import OpenSearchVectorSearch
import argparse




## S3_client
s3_client = boto3.client('s3')

## Bedrock client
bedrock_client = boto3.client(service_name="bedrock-runtime")


## Configuration for AWS authentication and OpenSearch client
credentials = boto3.Session().get_credentials()
awsauth = AWSV4SignerAuth(credentials, 'us-east-1', 'aoss')




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
    embeddings_model = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=bedrock_client)
    chunks_list=[chunk.page_content for chunk in chunks]
    embeddings = embeddings_model.embed_documents(chunks_list)
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
        bulk_size=1000
)

    return docsearch


# Func to do both generating and storing embeddings
def generate_store_embeddings(bedrock_client, chunks,awsauth,index_name):
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
def main(bucket_name, endpoint,index_name, local_path):

    ## Opensearch Client
    OpenSearch_client = OpenSearch(
        hosts=[{'host': endpoint, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        
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
    store_embeddings(embeddings, texts, meta_data ,endpoint, awsauth,index_name)
    print('End storing')


   

  




if __name__== "__main__":
    parser = argparse.ArgumentParser(description="Process PDF documents and store their embeddings.")
    parser.add_argument("--bucket_name", help="The S3 bucket name where documents are stored")
    parser.add_argument("--endpoint", help="The OpenSearch service endpoint")
    parser.add_argument("--index_name", help="The name of the OpenSearch index")
    parser.add_argument("--local_path", help="local path")
    args = parser.parse_args()
    main(args.bucket_name, args.endpoint, args.index_name, args.local_path)
