import base64
import gzip
import json
import re

def lambda_handler(event, context):
    # Decode and decompress the log data
    compressed_payload = base64.b64decode(event['awslogs']['data'])
    uncompressed_payload = gzip.decompress(compressed_payload)

    # Convert log data from JSON into a Python dictionary
    log_data = json.loads(uncompressed_payload)

    # Now you can access the log events as a Python list
    log_events = log_data['logEvents']

    # Iterate over each log event and print its content
    for log_event in log_events:
        log_line = log_event['message']
        request_id = re.search(r'RequestId: (.*?) ', log_line).group(1)
        duration = re.search(r'Duration: (.*?) ms', log_line).group(1)
        memory_size = re.search(r'Memory Size: (.*?) MB', log_line).group(1)
        max_memory_used = re.search(r'Max Memory Used: (.*?) MB', log_line).group(1)
        
        print(f"RequestId: {request_id}")
        print(f"Duration: {duration} ms")
        print(f"Memory Size: {memory_size} MB")
        print(f"Max Memory Used: {max_memory_used} MB")