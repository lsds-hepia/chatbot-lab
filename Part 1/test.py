import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain_community.embeddings import BedrockEmbeddings

# AWS and OpenSearch Configuration
host = 'd7gvxdj7jpz3h3bj0xq6.us-east-1.aoss.amazonaws.com'  
index_name = 'cloud_lecture'
awsauth = AWSV4SignerAuth(boto3.Session().get_credentials(), 'us-east-1', 'aoss')

# OpenSearch Client
opensearch_client = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
)

# Embeddings Client
bedrock_client = boto3.client(service_name="bedrock-runtime")

def get_embedding(question, bedrock_client):
    embeddings_model = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=bedrock_client)
    embedding = embeddings_model.embed_query(question)
    return embedding

def knn_query(vector, index_name):
    query_body = {
        "size": 10,
        "query": {
            "knn": {
                "vector_field": {
                    "vector": vector,
                    "k": 10
                }
            }
        }
    }
    response = opensearch_client.search(index=index_name, body=query_body)
    return response['hits']['hits']

def main():
    question = "What is FAAS?" 
    print("Generating embedding for the question...")
    question_embedding = get_embedding(question, bedrock_client)
    print("Querying the index for similar contents...")
    search_results = knn_query(question_embedding, index_name)
    print(search_results[0])
   

if __name__ == "__main__":
    main()
