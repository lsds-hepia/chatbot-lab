import boto3
import os
import tempfile
import io
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_aws import BedrockEmbeddings
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain_community.vectorstores import OpenSearchVectorSearch
from langchain.schema import Document


# AWS clients and authentication
s3_client = boto3.client('s3')
bedrock_client = boto3.client(service_name="bedrock-runtime")
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
                    "dimension": 1024,
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

    
## Split pages/text into chunks
def split_text(docs, chunk_size, chunk_overlap):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_documents(docs)   

    return chunks
 
## Generate embeddings 
def generate_embeddings(bedrock_client, chunks):
    embeddings_model = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0", client=bedrock_client)
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
        bulk_size=500,
        timeout = 120,
        max_chunk_bytes=10485760  # 10MB max chunk size
)

    return docsearch



# Lambda handler function
def lambda_handler(event, context):
    # Get bucket and key from the event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    print(bucket_name)
    key = event['Records'][0]['s3']['object']['key']
    print(key)
    
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    print(response)
    # Read endoint and index name
    endpoint = os.environ['ENDPOINT']
    print(endpoint)
    index_name = os.environ['INDEXNAME']
    print(index_name)
    
    # OpenSearch Client
    opensearch_client = OpenSearch(
        hosts=[{'host': endpoint, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )

     # Download PDF to Lambda /tmp
    tmp_path = os.path.join(tempfile.gettempdir(), os.path.basename(key))
    print(tmp_path)
    s3_client.download_file(bucket_name, key, tmp_path)

    # Load PDF with LangChain loader
    loader = PyPDFDirectoryLoader(os.path.dirname(tmp_path))
    docs = loader.load()


    chunks = split_text(docs, 1000, 100)
    create_index(opensearch_client, index_name)
    embeddings = generate_embeddings(bedrock_client, chunks)
    texts = [chunk.page_content for chunk in chunks]
    meta_data = [{'page': chunk.metadata['page'] + 1} for chunk in chunks]
    store_embeddings(embeddings, texts, meta_data, endpoint, awsauth, index_name)
   
    return {
        "statusCode": 200,
        "body": "Embeddings stored in OpenSearch"
        }

  