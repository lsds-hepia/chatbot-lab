# Creator: Abir Chebbi (abir.chebbi@hesge.ch)

import boto3
import os
import time
import argparse
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain_community.vectorstores import OpenSearchVectorSearch


## Clients for the three services used in this exercise:
## S3 stores the PDFs, Bedrock creates the embeddings,
## OpenSearch Serverless stores and searches the vectors.
def create_aws_clients(region, endpoint):

    ## S3 client
    s3_client = boto3.client('s3', region_name=region)

    ## Bedrock client
    bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=region)

    ## Configuration for AWS authentication
    credentials = boto3.Session().get_credentials()
    awsauth = AWSV4SignerAuth(credentials, region, 'aoss')

    ## OpenSearch client
    ## A new collection is slow to answer its first requests, so allow more than
    ## the 10 second default and retry instead of failing.
    opensearch_client = OpenSearch(
        hosts=[{'host': endpoint, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=600,
        max_retries=10,
        retry_on_timeout=True,
    )

    return s3_client, bedrock_client, awsauth, opensearch_client


## Create Index in Opensearch
def create_index(client, index_name, dimension):
    indexBody = {
        "settings": {
            "index.knn": True
        },
        "mappings": {
            "properties": {
                "vector_field": {
                    "type": "knn_vector",
                    "dimension": dimension,
                    "method": {
                        "engine": "faiss",
                        "name": "hnsw"
                    }
                }
            }
        }
    }

    try:
        create_response = client.indices.create(index=index_name, body=indexBody)
        print('\nCreating index:')
        print(create_response)
    except Exception as e:
        if 'resource_already_exists_exception' in str(e):
            ## An index built with another embedding model has the wrong vector size
            existing = client.indices.get_mapping(index=index_name)
            existing_dim = existing[index_name]['mappings']['properties']['vector_field']['dimension']
            if existing_dim != dimension:
                raise SystemExit(
                    f"Index '{index_name}' already exists with dimension {existing_dim}, "
                    f"but the embedding model produces {dimension}. "
                    f"Delete it or choose another --index_name."
                )
            print(f"Index '{index_name}' already exists, reusing it.")
        else:
            raise


## Load docs from S3
def download_documents(s3_client, bucket_name, local_dir):
    os.makedirs(local_dir, exist_ok=True)
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    if 'Contents' not in response:
        raise SystemExit(f"Bucket '{bucket_name}' is empty. Run create-S3-and-put-docs.py first.")
    count = 0
    for item in response['Contents']:
        key = item['Key']
        if key.endswith('.pdf'):
            local_filename = os.path.join(local_dir, os.path.basename(key))
            print(f"Downloading {key} ...")
            s3_client.download_file(Bucket=bucket_name, Key=key, Filename=local_filename)
            count += 1
    print(f"Downloaded {count} PDF file(s) to {local_dir}")


## Split pages/text into chunks
def split_text(docs, chunk_size, chunk_overlap):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_documents(docs)
    return chunks


## Generate embeddings
def generate_embeddings(embeddings_model, chunks):
    chunks_list = [chunk.page_content for chunk in chunks]
    embeddings = embeddings_model.embed_documents(chunks_list)
    return embeddings


## A new collection needs a moment before it answers its first request
def wait_until_ready(client, index_name, attempts=20, delay=15):
    for attempt in range(attempts):
        try:
            client.count(index=index_name)
            print("Collection is ready.")
            return
        except Exception:
            print(f"  waiting for the collection to be ready ({attempt + 1}/{attempts})...")
            time.sleep(delay)
    print("Collection still not responding; trying to store anyway.")


## Store generated embeddings into an OpenSearch index
def store_embeddings(embeddings, texts, meta_data, embeddings_model, host, awsauth, index_name):
    docsearch = OpenSearchVectorSearch.from_embeddings(
        embeddings,
        texts,
        embeddings_model,
        metadatas=meta_data,
        opensearch_url=f'https://{host}:443',
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        index_name=index_name,
        bulk_size=1000,
        timeout=600,
        max_retries=10,
        retry_on_timeout=True,
    )
    return docsearch


## main
def main(bucket_name, endpoint, index_name, download_path, region, embed_model_id):

    s3_client, bedrock_client, awsauth, OpenSearch_client = create_aws_clients(region, endpoint)

    embeddings_model = BedrockEmbeddings(model_id=embed_model_id, client=bedrock_client)

    download_documents(s3_client, bucket_name, download_path)

    loader = PyPDFDirectoryLoader(download_path)
    docs = loader.load()
    if not docs:
        raise SystemExit(f"No readable PDF pages found in {download_path}.")

    print('Start chunking')
    chunks = split_text(docs, 1000, 100)
    print(f"Produced {len(chunks)} chunk(s). First chunk:")
    print(chunks[0].page_content[:300])

    ## The index must have the same vector size as the embedding model
    dimension = len(embeddings_model.embed_query("dimension probe"))
    print(f"\nModel '{embed_model_id}' returns {dimension}-dimensional vectors.")
    create_index(OpenSearch_client, index_name, dimension)

    print('Start vectorising')
    embeddings = generate_embeddings(embeddings_model, chunks)
    print(f"Generated {len(embeddings)} embedding vector(s).")

    texts = [chunk.page_content for chunk in chunks]
    ## Prepare metadata for each chunk
    meta_data = [{'source': chunk.metadata['source'], 'page': chunk.metadata.get('page', 0) + 1} for chunk in chunks]

    wait_until_ready(OpenSearch_client, index_name)

    print('Start storing')
    for attempt in range(3):
        try:
            store_embeddings(embeddings, texts, meta_data, embeddings_model, endpoint, awsauth, index_name)
            break
        except Exception as e:
            if attempt == 2:
                raise
            print(f"  storing failed ({type(e).__name__}), retrying in 30s...")
            time.sleep(30)
    print('End storing')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process PDF documents and store their embeddings.")
    parser.add_argument("--bucket_name", required=True, help="The S3 bucket name where documents are stored")
    parser.add_argument("--endpoint", required=True, help="The OpenSearch service endpoint (without https://)")
    parser.add_argument("--index_name", required=True, help="The name of the OpenSearch index")
    parser.add_argument("--download_path", default="./downloaded_pdfs",
                        help="Temporary local folder the PDFs are downloaded into "
                             "(default: ./downloaded_pdfs, created if missing)")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--embed_model_id", default="amazon.titan-embed-text-v2:0",
                        help="Bedrock embedding model ID (default: amazon.titan-embed-text-v2:0)")
    args = parser.parse_args()
    main(args.bucket_name, args.endpoint, args.index_name, args.download_path, args.region, args.embed_model_id)
