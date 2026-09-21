# Creator: Abir Chebbi (abir.chebbi@hesge.ch)

import boto3
import base64
import argparse

APP_DIR = "/home/ubuntu/chatbot-lab"
VENV_DIR = "/home/ubuntu/chatbotlab"
LOG_FILE = "/var/log/chatbot-lab.log"

## Canonical's AWS account, so we get the official Ubuntu images
UBUNTU_OWNER = "099720109477"
UBUNTU_PATTERN = "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"


## Read a file we want to send to the instance. The trailing newline is dropped
## because the heredoc adds one back before its closing marker.
def read_file(filepath):
    with open(filepath, 'r') as file:
        return file.read().rstrip('\n')


## Find the most recent official Ubuntu 24.04 image
def latest_ubuntu_ami(region):
    ec2 = boto3.client('ec2', region_name=region)
    images = ec2.describe_images(
        Owners=[UBUNTU_OWNER],
        Filters=[
            {'Name': 'name', 'Values': [UBUNTU_PATTERN]},
            {'Name': 'state', 'Values': ['available']},
        ],
    )['Images']
    if not images:
        raise SystemExit("No Ubuntu 24.04 image found in this region.")
    newest = sorted(images, key=lambda i: i['CreationDate'])[-1]
    print(f"Using Ubuntu image {newest['ImageId']} ({newest['Name']})")
    return newest['ImageId']


## Build the script the instance runs at first boot. The application is sent
## with the instance, so there is no image to prepare and nothing to keep in
## sync. Each heredoc marker is quoted so the shell copies the content
## literally, and sits at the start of its line, otherwise bash never closes
## the heredoc.
def build_user_data(app_code, requirements, config_content):
    return f"""#!/bin/bash
exec > >(tee -a {LOG_FILE}) 2>&1
echo "=== chatbot-lab bootstrap started at $(date) ==="

mkdir -p {APP_DIR}

cat <<'APP_EOF' > {APP_DIR}/chatbot.py
{app_code}
APP_EOF

cat <<'REQ_EOF' > {APP_DIR}/requirements.txt
{requirements}
REQ_EOF

cat <<'CFG_EOF' > {APP_DIR}/config.ini
{config_content}
CFG_EOF

chown -R ubuntu:ubuntu {APP_DIR}
chmod 600 {APP_DIR}/config.ini

echo "=== installing dependencies ==="
apt-get update -y
apt-get install -y python3-venv
python3 -m venv {VENV_DIR}
{VENV_DIR}/bin/pip install --upgrade pip
{VENV_DIR}/bin/pip install -r {APP_DIR}/requirements.txt
chown -R ubuntu:ubuntu {VENV_DIR}

echo "=== starting streamlit ==="
cd {APP_DIR}
nohup {VENV_DIR}/bin/streamlit run chatbot.py \\
    --server.address 0.0.0.0 --server.port 8501 \\
    --server.headless true >> {LOG_FILE} 2>&1 &

echo "=== bootstrap finished at $(date) ==="
"""


def create_instance(ami_id, key_pair_name, security_group_id, instance_type, instance_profile, region):

    script = build_user_data(
        read_file('chatbot.py'),
        read_file('requirements.txt'),
        read_file('config.ini'),
    )

    ## EC2 accepts at most 16 KB of user data
    print(f"Startup script: {len(script)} bytes")
    if len(script) > 16000:
        raise SystemExit("The startup script is too large for EC2 user data.")

    encoded_script = base64.b64encode(script.encode()).decode('utf-8')

    ec2 = boto3.resource('ec2', region_name=region)
    instance = ec2.create_instances(
        ImageId=ami_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        KeyName=key_pair_name,
        SecurityGroupIds=[security_group_id],
        UserData=encoded_script,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': 'chatbot-lab'}]
        }],
        ## The instance gets its AWS credentials from this role
        IamInstanceProfile={'Name': instance_profile},
    )
    return instance


def main(ami_id, key_pair_name, security_group_id, instance_type, instance_profile, region):

    if not ami_id:
        ami_id = latest_ubuntu_ami(region)

    print("Creating an EC2 instance")
    instance = create_instance(ami_id, key_pair_name, security_group_id,
                               instance_type, instance_profile, region)
    inst = instance[0]
    print("Instance created with ID:", inst.id)

    print("Waiting for the instance to start (this takes a minute)...")
    inst.wait_until_running()
    inst.reload()
    print("Public IP:", inst.public_ip_address)
    print(f"\nThe app will be available at: http://{inst.public_ip_address}:8501")
    print("The instance still has to install the dependencies, which takes a few minutes.")
    print("If the page does not load, connect and read the log:")
    print(f"  ssh -i [YourKey.pem] ubuntu@{inst.public_ip_address}")
    print(f"  sudo cat {LOG_FILE}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create an EC2 instance to run the chatbot")
    parser.add_argument("--key_pair_name", required=True, help="The name of the key pair to use for the instance")
    parser.add_argument("--security_group_id", required=True, help="The ID of the security group to use for the instance")
    parser.add_argument("--instance_profile", required=True,
                        help="Instance profile for the role your instructor created")
    parser.add_argument("--ami_id", default=None, help="AMI to use (default: the latest Ubuntu 24.04)")
    parser.add_argument("--instance_type", default="t3.micro", help="EC2 instance type (default: t3.micro)")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    args = parser.parse_args()
    main(args.ami_id, args.key_pair_name, args.security_group_id,
         args.instance_type, args.instance_profile, args.region)
