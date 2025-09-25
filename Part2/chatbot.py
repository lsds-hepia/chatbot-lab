# Creator: Abir Chebbi (abir.chebbi@hesge.ch)
import streamlit as st
from openai import AzureOpenAI
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from opensearchpy import OpenSearch, RequestsHttpConnection
from langchain_core.prompts import PromptTemplate
import configparser
import os

def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config

config = load_config()

# Azure OpenAI configuration
azure_endpoint = config.get('azure', 'azure_openai_endpoint')
azure_api_key = config.get('azure', 'azure_openai_api_key')
azure_api_version = config.get('azure', 'azure_api_version', fallback='2024-02-01')
chat_deployment_name = config.get('azure', 'chat_deployment_name')
embedding_deployment_name = config.get('azure', 'embedding_deployment_name')

# OpenSearch configuration (keeping this for vector search)
endpoint = config.get('opensearch', 'endpoint')
index_name = config.get('opensearch', 'index_name')

# Azure OpenAI Client
azure_client = AzureOpenAI(
    azure_endpoint=azure_endpoint,
    api_key=azure_api_key,
    api_version=azure_api_version
)

# configuring streamlit page settings
st.set_page_config(
    page_title="cloud lecture lab",
    page_icon="💬",
    layout="centered"
)


# streamlit page title
st.title("Chat with your lecture")




# OpenSearch Client (assuming you're using a basic auth or no auth OpenSearch)
def opensearch_client(endpoint, username=None, password=None):
    if username and password:
        # Basic authentication
        client = OpenSearch(
            hosts=[{'host': endpoint, 'port': 443}],
            http_auth=(username, password),
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )
    else:
        # No authentication (for development/testing)
        client = OpenSearch(
            hosts=[{'host': endpoint, 'port': 9200}],  # Default OpenSearch port
            use_ssl=False,
            verify_certs=False,
            connection_class=RequestsHttpConnection,
        )
    return client

def get_embedding(question, azure_client=None):
    """Generate embeddings using Azure OpenAI"""
    try:
        embeddings_model = AzureOpenAIEmbeddings(
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version=azure_api_version,
            azure_deployment=embedding_deployment_name,
        )
        print(f"Using Azure OpenAI embedding model: {embedding_deployment_name}")
        embedding = embeddings_model.embed_query(question)
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        raise ValueError("Failed to generate embedding with Azure OpenAI")
    
    embedding = embeddings_model.embed_query(question)
    return embedding

def similarity_search(client, embed_query, index_name):
    query_body = {
        "size": 5,
        "query": {
            "knn": {
                "vector_field": {
                    "vector": embed_query,
                    "k": 5
                }
            }
        }
    }
    response = client.search(index=index_name, body=query_body)
    return response['hits']['hits']

def prepare_prompt(question, context):
    template = """
    You are a Professor. The student will ask you a questions about the lecture. 
    Use following piece of context to answer the question. 
    If you don't know the answer, just say you don't know. 

    Context:   <context>
    {context}
    </context>
    Question: {question}
    Answer: 

    """

    prompt = PromptTemplate(
    template=template, 
    input_variables=['context', 'question']
    )
    prompt_formatted_str = prompt.format(context=context, question= question)
    return prompt_formatted_str

def generate_answer(prompt):
    """Generate answer using Azure OpenAI"""
    try:
        model = AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version=azure_api_version,
            azure_deployment=chat_deployment_name,
            temperature=0.1
        )
        print(f"Using Azure OpenAI chat model: {chat_deployment_name}")
        answer = model.invoke(prompt)
        return answer
    except Exception as e:
        print(f"Error generating answer: {e}")
        raise ValueError("Failed to generate answer with Azure OpenAI")


def main():

    oss_client = opensearch_client(endpoint)

    # initialize chat session in streamlit if not already present
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

        
    # display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


    # input field for user's message
    user_prompt = st.chat_input("Ask a question for your knowledge base")

    if user_prompt:
    # add user's message to chat and display it
        st.chat_message("user").markdown(user_prompt)
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        # Generate and display answer
        print(user_prompt)
 
        embed_question = get_embedding(user_prompt)
        print(embed_question)
        sim_results = similarity_search(oss_client, embed_question, index_name)
        context = [i['_source']['text'] for i in sim_results]
        print(context)
        prompt = prepare_prompt(user_prompt, context)
        print(prompt)
        answer = generate_answer(prompt)
        st.session_state.chat_history.append({"role": "system", "content": answer.content})
        for message in st.session_state.chat_history[-1:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

if __name__== "__main__":
    main()

 
