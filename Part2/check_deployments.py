#!/usr/bin/env python3
"""
Script to check what deployments are available in your Azure OpenAI resource
"""
import configparser
from openai import AzureOpenAI
import requests

def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config

def list_deployments():
    """List all deployments in the Azure OpenAI resource"""
    config = load_config()
    
    # Get configuration
    azure_endpoint = config.get('azure', 'azure_openai_endpoint')
    azure_api_key = config.get('azure', 'azure_openai_api_key')
    azure_api_version = config.get('azure', 'azure_api_version', fallback='2024-02-01')
    
    print(f"Checking deployments in: {azure_endpoint}")
    print(f"API Version: {azure_api_version}")
    print("-" * 50)
    
    # Create the Azure OpenAI client
    client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_api_key,
        api_version=azure_api_version
    )
    
    try:
        # Use the REST API to list deployments
        url = f"{azure_endpoint}openai/deployments?api-version={azure_api_version}"
        headers = {
            "api-key": azure_api_key,
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            deployments = response.json()
            
            if 'data' in deployments and deployments['data']:
                print("Available deployments:")
                print("-" * 30)
                
                for deployment in deployments['data']:
                    name = deployment.get('id', 'Unknown')
                    model = deployment.get('model', 'Unknown')
                    status = deployment.get('status', 'Unknown')
                    
                    print(f"Deployment Name: {name}")
                    print(f"Model: {model}")
                    print(f"Status: {status}")
                    print("-" * 20)
                    
                    # Suggest which ones to use
                    if 'embedding' in model.lower() or 'ada' in model.lower():
                        print(f"👉 Use '{name}' for embedding_deployment_name")
                    elif 'gpt' in model.lower():
                        print(f"👉 Use '{name}' for chat_deployment_name")
                    print()
            else:
                print("No deployments found!")
                print("You need to create deployments in the Azure Portal:")
                print("1. Go to https://portal.azure.com")
                print("2. Navigate to your Azure OpenAI resource")
                print("3. Go to 'Model deployments' or 'Deployments'")
                print("4. Create deployments for:")
                print("   - An embedding model (like text-embedding-ada-002)")
                print("   - A chat model (like gpt-4 or gpt-3.5-turbo)")
        else:
            print(f"Error getting deployments: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your API key is correct")
        print("2. Check your endpoint URL is correct")
        print("3. Make sure your Azure OpenAI resource has deployments created")

if __name__ == "__main__":
    list_deployments()
