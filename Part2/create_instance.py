# Creator: Abir Chebbi (abir.chebbi@hesge.ch)

import boto3
import base64
import argparse
import textwrap

APP_DIR = "/home/ubuntu/chatbot-lab/Part2"
VENV_DIR = "/home/ubuntu/chatbotlab"
LOG_FILE = "/var/log/chatbot-lab.log"


# Function to read the content of config.ini
def get_config_content(filepath):
    with open(filepath, 'r') as file:
        return file.read()


def build_user_data(config_content):
    """Build the script that writes config.ini and starts the chatbot at boot.

    Keep 'EOT' at the start of its line, otherwise bash does not close the heredoc.
    """
    script = textwrap.dedent(f"""\
        #!/bin/bash
        exec > >(tee -a {LOG_FILE}) 2>&1
        echo "=== chatbot-lab bootstrap started at $(date) ==="

        if [ ! -d "{APP_DIR}" ]; then
            echo "ERROR: {APP_DIR} not found. The AMI does not contain the lab code."
            exit 1
        fi

        cat <<'EOT' > {APP_DIR}/config.ini
        {{CONFIG}}
        EOT

        chown ubuntu:ubuntu {APP_DIR}/config.ini
        chmod 600 {APP_DIR}/config.ini

        if [ ! -f "{VENV_DIR}/bin/activate" ]; then
            echo "venv missing, creating it"
            apt-get update -y && apt-get install -y python3-venv
            python3 -m venv {VENV_DIR}
            {VENV_DIR}/bin/pip install --upgrade pip
            {VENV_DIR}/bin/pip install -r {APP_DIR}/requirements.txt
        fi

        cd {APP_DIR}
        echo "=== starting streamlit ==="
        nohup {VENV_DIR}/bin/streamlit run chatbot.py \\
            --server.address 0.0.0.0 --server.port 8501 \\
            --server.headless true >> {LOG_FILE} 2>&1 &
        echo "=== bootstrap finished at $(date) ==="
    """)
    return script.replace("{CONFIG}", config_content.strip())


def create_instance(ami_id, key_pair_name, security_group_id, instance_type, iam_instance_profile):

    # Load the config content
    config_content = get_config_content('config.ini')
    ec2 = boto3.resource('ec2')

    script = build_user_data(config_content)
    encoded_script = base64.b64encode(script.encode()).decode('utf-8')

    kwargs = dict(
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
    )
    if iam_instance_profile:
        kwargs['IamInstanceProfile'] = {'Name': iam_instance_profile}

    instance = ec2.create_instances(**kwargs)
    return instance


def main(ami_id, key_pair_name, security_group_id, instance_type, iam_instance_profile):

    print("Creating an EC2 instance")
    instance = create_instance(ami_id, key_pair_name, security_group_id, instance_type, iam_instance_profile)
    inst = instance[0]
    print("Instance created with ID:", inst.id)

    print("Waiting for the instance to start (this takes a minute)...")
    inst.wait_until_running()
    inst.reload()
    print("Public IP:", inst.public_ip_address)
    print(f"\nThe app will be available at: http://{inst.public_ip_address}:8501")
    print("Streamlit needs another minute or so to boot. If it does not come up, SSH in and check:")
    print(f"  sudo cat {LOG_FILE}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create an EC2 instance to run the chatbot")
    parser.add_argument("--ami_id", required=True, help="The ID of the AMI to use for the instance")
    parser.add_argument("--key_pair_name", required=True, help="The name of the key pair to use for the instance")
    parser.add_argument("--security_group_id", required=True, help="The ID of the security group to use for the instance")
    parser.add_argument("--instance_type", default="t3.micro", help="EC2 instance type (default: t3.micro)")
    parser.add_argument("--iam_instance_profile", default=None,
                        help="Name of an IAM instance profile granting Bedrock + OpenSearch Serverless "
                             "access. Recommended: use this instead of putting AWS keys in config.ini.")
    args = parser.parse_args()
    main(args.ami_id, args.key_pair_name, args.security_group_id, args.instance_type, args.iam_instance_profile)
