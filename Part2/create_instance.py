# Creator: Abir Chebbi (abir.chebbi@hesge.ch)

import boto3
import base64
import argparse

# Function to read the content of config.ini
def get_config_content(filepath):
    with open(filepath, 'r') as file:
        return file.read()


def create_instance(ami_id, key_pair_name, security_group_id):

    # Load the config content
    config_content = get_config_content('config.ini')
    ec2 = boto3.resource('ec2')
    # User code that's executed when the instance starts
    script = f"""#!/bin/bash
    cat <<EOT > /home/ubuntu/chatbot-lab/Part2/config.ini
    {config_content}
    EOT
    source /home/ubuntu/chatbotlab/bin/activate
    ## Run the application 
    cd /home/ubuntu/chatbot-lab/Part2
    streamlit run chatbot.py 
    """
    encoded_script = base64.b64encode(script.encode()).decode('utf-8')
    # Create a new EC2 instance
    instance = ec2.create_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName=key_pair_name,
        SecurityGroupIds=[security_group_id],
        UserData=encoded_script
    )
    return instance
 

def main(ami_id, key_pair_name, security_group_id):
    
    print("Creating an EC2 instance")
    instance = create_instance(ami_id, key_pair_name, security_group_id)
    print("Instance created with ID:", instance[0].id)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create an EC2 instance to run the chatbot")
    parser.add_argument("--ami_id", help="The ID of the AMI to use for the instance")
    parser.add_argument("--key_pair_name", help="The name of the key pair to use for the instance")
    parser.add_argument("--security_group_id", help="The ID of the security group to use for the instance")
    args = parser.parse_args()
    main(args.ami_id, args.key_pair_name, args.security_group_id)