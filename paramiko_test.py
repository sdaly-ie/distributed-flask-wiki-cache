import os
import paramiko
import shlex

instance_ip = os.getenv("EC2_INSTANCE_IP", "YOUR_EC2_PUBLIC_IP")
security_key_file = os.getenv("EC2_KEY_FILE", "/path/to/YOUR_KEY.pem")
search_term = "Barack Obama"

remote_python = os.getenv("REMOTE_PYTHON", "/home/ubuntu/ct5169-wiki/venv/bin/python")
remote_script = os.getenv("REMOTE_SCRIPT", "/home/ubuntu/ct5169-wiki/wiki.py")

cmd = f'{remote_python} {remote_script} {shlex.quote(search_term)}'

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    key = paramiko.RSAKey.from_private_key_file(security_key_file)
    client.connect(hostname=instance_ip, username="ubuntu", pkey=key)

    stdin, stdout, stderr = client.exec_command(cmd)
    stdin.close()

    errors = stderr.read().decode().strip()
    output = stdout.read().decode().strip()

    print("ERRORS:")
    print(errors if errors else "None")

    print("\nOUTPUT:")
    print(output if output else "No output returned")

    client.close()

except Exception as e:
    print("EXCEPTION:")
    print(str(e))
