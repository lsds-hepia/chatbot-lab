# Creator: Abir Chebbi (abir.chebbi@hesge.ch)

import boto3
import base64

# Function to read the content of config.ini
def get_config_content(filepath):
    with open(filepath, 'r') as file:
        return file.read()

# Load the config content
config_content = get_config_content('config.ini')


ec2 = boto3.resource('ec2')



# User code that's executed when the instance starts
script = f"""#!/bin/bash
cat <<EOT > /home/ubuntu/chatbot-lab/Part2/config.ini
{config_content}
EOT
source /home/ubuntu/chatbotlab/bin/activate
## Run the apllication 
cd /home/ubuntu/chatbot-lab/Part2
streamlit run main.py 
"""

encoded_script = base64.b64encode(script.encode()).decode('utf-8')

# Create a new EC2 instance
instance = ec2.create_instances(
    ImageId='ami-05747e7a13dac9d14',
    MinCount=1,
    MaxCount=1,
    InstanceType='t2.micro',
    KeyName='group-14-key-pair',
    SecurityGroupIds=['sg-06f3ca7153db92958'],
    UserData=encoded_script
)
print("Instance created with ID:", instance[0].id)
   



