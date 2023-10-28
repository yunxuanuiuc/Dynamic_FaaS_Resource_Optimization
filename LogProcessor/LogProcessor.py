import boto3
import re
import time

def lambda_handler(event, context):
    
    startTimeStamp = 0
    client = boto3.client('logs')

    while (True):
        
        try:
            response = client.filter_log_events(
                logGroupName = '/aws/lambda/CpuIntensiveFunction',
                startTime = startTimeStamp + 1
            )
            
            for event in response['events']:
                if not event['message'].startswith('REPORT RequestId'):
                    continue
                
                log_line = event['message']
                
                request_id = re.search(r'RequestId: (.*?) ', log_line).group(1)
                duration = re.search(r'Duration: (.*?) ms', log_line).group(1)
                memory_size = re.search(r'Memory Size: (.*?) MB', log_line).group(1)
                max_memory_used = re.search(r'Max Memory Used: (.*?) MB', log_line).group(1)
                
                print(f"RequestId: {request_id}")
                print(f"Duration: {duration} ms")
                print(f"Memory Size: {memory_size} MB")
                print(f"Max Memory Used: {max_memory_used} MB")
                    
                startTimeStamp = event['timestamp']
        except Exception as error:
            print(error)