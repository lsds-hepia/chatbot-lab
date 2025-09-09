# Creator: Abir Chebbi (abir.chebbi@hesge.ch)

import boto3
import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain_community.vectorstores import OpenSearchVectorSearch

## Bedrock client
bedrock_client = boto3.client(service_name="bedrock-runtime")


## Configuration for AWS authentication and OpenSearch client
credentials = boto3.Session().get_credentials()
awsauth = AWSV4SignerAuth(credentials, 'us-east-1', 'aoss')

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
        create_response = client.indices.create(index=index_name, body=indexBody)
        print('\nCreating index:')
        print(create_response)
    except Exception as e:
        print(e)
        print("(Index likely already exists?)") 





## Load docs from local directory
def check_documents(local_dir):
    if not os.path.exists(local_dir):
        print(f"Directory {local_dir} does not exist!")
        return False
    
    pdf_files = [f for f in os.listdir(local_dir) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"No PDF files found in {local_dir}")
        return False
    
    print(f"Found {len(pdf_files)} PDF files in {local_dir}")
    return True

## Check for existing documents in OpenSearch to avoid duplicates
def get_existing_documents(client, index_name):
    try:
        query_body = {
            "size": 1000,
            "_source": ["source"],
            "query": {"match_all": {}}
        }
        response = client.search(index=index_name, body=query_body)
        existing_sources = set()
        for hit in response['hits']['hits']:
            if 'source' in hit['_source']:
                existing_sources.add(hit['_source']['source'])
        return existing_sources
    except Exception as e:
        print(f"Could not retrieve existing documents: {e}")
        return set()

## Filter out chunks from documents that already exist
def filter_new_chunks(chunks, existing_sources):
    new_chunks = []
    for chunk in chunks:
        if chunk.metadata['source'] not in existing_sources:
            new_chunks.append(chunk)
    return new_chunks

   
    



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
        bulk_size=1000,  # Increased to handle more documents
        timeout=300,     # Increased timeout to 5 minutes
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
        bulk_size=1000,  # Increased to handle more documents
        timeout=300,     # Increased timeout to 5 minutes
        max_chunk_bytes=10485760  # 10MB max chunk size
)

    return docsearch



## main 
def vectorize(endpoint, index_name, local_path):

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


    # Check if documents exist in local directory
    if not check_documents(local_path):
        return
    
    # Load documents directly from local directory
    loader = PyPDFDirectoryLoader(local_path)
    docs = loader.load()
    print('Start chunking')
    chunks = split_text(docs, 1000, 100)
    print(f"Created {len(chunks)} chunks")
    if chunks:
        print(chunks[0])  # Show first chunk instead of second
    
    create_index(OpenSearch_client, index_name)
    
    # Check for existing documents to avoid duplicates
    existing_sources = get_existing_documents(OpenSearch_client, index_name)
    if existing_sources:
        print(f"Found {len(existing_sources)} existing documents in index")
    
    # Filter out chunks from documents that already exist
    new_chunks = filter_new_chunks(chunks, existing_sources)
    
    if not new_chunks:
        print("No new documents to process. All documents already exist in the index.")
        return
    
    print(f"Processing {len(new_chunks)} new chunks (filtered from {len(chunks)} total)")
    
    print('Start vectorising')
    embeddings = generate_embeddings(bedrock_client, new_chunks)
    print(f"Generated {len(embeddings)} embeddings")
    if embeddings:
        print(f"First embedding dimension: {len(embeddings[0])}")
    
    texts = [chunk.page_content for chunk in new_chunks]
    # Prepare metadata for each chunk
    meta_data = [{'source': chunk.metadata['source'], 'page': chunk.metadata['page'] + 1} for chunk in new_chunks]
    print('Start storing')
    store_embeddings(embeddings, texts, meta_data, endpoint, awsauth, index_name)
    print('End storing')
    


