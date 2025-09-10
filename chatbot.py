# Creator: Abir Chebbi (abir.chebbi@hesge.ch)
import boto3
import streamlit as st
from langchain_aws import BedrockEmbeddings
from langchain_aws import ChatBedrock
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from langchain_core.prompts import PromptTemplate
import configparser


def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config

config = load_config()

aws_access_key_id = config.get('aws', 'aws_access_key_id')
aws_secret_access_key = config.get('aws', 'aws_secret_access_key')
region = config.get('aws', 'region')
endpoint = config.get('opensearch', 'endpoint')
index_name = config.get('opensearch', 'index_name')

# Embeddings Client
bedrock_client = boto3.client(service_name="bedrock-runtime", 
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key, region_name=region)

# configuring streamlit page settings
st.set_page_config(
    page_title="Business Knowledge Assistant",
    page_icon="💼",
    layout="centered"
)


# streamlit page title
st.title("💼 Ask Your Data")
st.subheader("Get instant insights from your business documents")

# Add document upload section
st.sidebar.title("📄 Upload Business Documents")
uploaded_files = st.sidebar.file_uploader(
    "Upload reports, presentations, or any business documents",
    type=['pdf', 'txt', 'docx'],
    accept_multiple_files=True
)

if uploaded_files:
    st.sidebar.success(f"✅ {len(uploaded_files)} file(s) uploaded")
    
    # Check if these files have already been processed
    file_names = [file.name for file in uploaded_files]
    session_key = f"processed_files_{hash(tuple(sorted(file_names)))}"
    
    if session_key not in st.session_state:
        # Auto-save and vectorize uploaded documents
        import os
        
        # Create uploads directory if it doesn't exist
        uploads_dir = "uploaded_documents"
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        
        saved_files = []
        for file in uploaded_files:
            # Save file to uploads directory
            file_path = os.path.join(uploads_dir, file.name)
            with open(file_path, "wb") as f:
                f.write(file.getbuffer())
            saved_files.append(file.name)
        
        st.sidebar.success(f"📁 Saved {len(saved_files)} files to {uploads_dir}/")
        
        for filename in saved_files:
            st.sidebar.write(f"- {filename}")
        
        # Auto-vectorize uploaded documents
        st.sidebar.info("🔄 Auto-vectorizing documents...")
        try:
            from vectorise_store import vectorize
            with st.sidebar:
                with st.spinner("Processing and vectorizing documents..."):
                    vectorize(endpoint, index_name, uploads_dir)
            st.sidebar.success("✅ Documents successfully vectorized and ready for chat!")
            
            # Mark files as processed
            st.session_state[session_key] = True
            
        except Exception as e:
            st.sidebar.error(f"❌ Error vectorizing documents: {e}")
            import traceback
            st.sidebar.text_area("Error Details", traceback.format_exc(), height=150)
    else:
        # Files already processed
        st.sidebar.info("📚 Documents already processed and ready for chat!")
        for file in uploaded_files:
            st.sidebar.write(f"- {file.name}")




# OpenSearch Client
def ospensearch_client(endpoint):
    session = boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region
    )
    awsauth = AWSV4SignerAuth(session.get_credentials(), region, 'aoss')
    client = OpenSearch(
    hosts=[{'host': endpoint, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    )
    return client

def get_embedding(question, bedrock_client):
    # Try multiple model IDs in order of preference (same as vectorization script)
    model_ids = [
        "amazon.titan-embed-text-v2:0",    # Latest version
        "amazon.titan-embed-text-v1",      # Previous version  
        "cohere.embed-english-v3"          # Alternative
    ]
    
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
    You are a knowledgeable business consultant and data analyst. A manager is asking you questions about their business documents and data. 
    
    Provide clear, actionable insights based on the information available. Use business-friendly language and avoid technical jargon. 
    Focus on practical implications and key takeaways that would help in decision-making.
    
    If you don't have enough information to provide a complete answer, clearly state what's missing and suggest what additional data might be needed.

    Context from business documents: <context>
    {context}
    </context>
    
    Manager's Question: {question}
    
    Business Insight:

    """

    prompt = PromptTemplate(
    template=template, 
    input_variables=['context', 'question']
    )
    prompt_formatted_str = prompt.format(context=context, question= question)
    return prompt_formatted_str

def generate_answer(prompt):
    model = ChatBedrock(model_id="anthropic.claude-v2", model_kwargs={"temperature": 0.1}, client=bedrock_client)
    answer = model.invoke(prompt)
    return answer


def main():

    oss_client= ospensearch_client(endpoint)

    # initialize chat session in streamlit if not already present
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

        
    # display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


    # input field for user's message
    user_prompt = st.chat_input("Ask a question about your business data and documents...")

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
        st.session_state.chat_history.append({"role": "system", "content": answer.content})
        for message in st.session_state.chat_history[-1:]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

if __name__== "__main__":
    main()

 
