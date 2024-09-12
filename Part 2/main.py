import boto3
import streamlit as st
## Bedrock
from langchain.llms.bedrock import Bedrock
## prompt and chain
from langchain.chains import RetrievalQA
from langchain_community.embeddings import BedrockEmbeddings
from langchain_community.chat_models import BedrockChat
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain import PromptTemplate
import argparse

# Embeddings Client
bedrock_client = boto3.client(service_name="bedrock-runtime")

# configuring streamlit page settings
st.set_page_config(
    page_title="cloud lecture lab",
    page_icon="💬",
    layout="centered"
)


# streamlit page title
st.title("Chat with your lecture")




# OpenSearch Client
def ospensearch_client(endpoint):
    awsauth = AWSV4SignerAuth(boto3.Session().get_credentials(), 'us-east-1', 'aoss')
    client = OpenSearch(
    hosts=[{'host': endpoint, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    )
    return client

def get_embedding(question, bedrock_client):
    embeddings_model = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1", client=bedrock_client)
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
    model = BedrockChat(model_id="anthropic.claude-v2", model_kwargs={"temperature": 0.1})
    answer = model.invoke(prompt)
    return answer


def main(endpoint, index_name):

    oss_client= ospensearch_client(endpoint)

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
 
        embed_question= get_embedding(user_prompt,bedrock_client)
        print(embed_question)
        sim_results = similarity_search(oss_client, embed_question, index_name)
        context = [i['_source']['text'] for i in sim_results]
        print(context)
        prompt = prepare_prompt(user_prompt, context)
        print(prompt)
        answer = generate_answer(prompt)
        st.session_state.chat_history.append({"role": "system", "content": answer})
        for message in st.session_state.chat_history[-1:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

if __name__== "__main__":
    # Argument parsing
    parser = argparse.ArgumentParser(description='Configure endpoint and index name for the lecture chat application.')
    parser.add_argument('--endpoint', type=str, help='The endpoint for the OpenSearch service.')
    parser.add_argument('--index_name', type=str, help='The index name for storing embeddings.')
    args = parser.parse_args()
    main(args.endpoint, args.index_name)

 
