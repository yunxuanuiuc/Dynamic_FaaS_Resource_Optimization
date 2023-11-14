import gzip
import json
import random
import string
import sys

def lambda_handler(event, context):

    request_id = context.aws_request_id
    payload_size = sys.getsizeof(json.dumps(event))
    function_type = 'CPU'
    function_id = 'dfaastest_decompress'
    print(f'Custom REPORT RequestId: {request_id} Function Type: {function_type} Function Id: {function_id} Payload Size: {payload_size}')

    content = event["body"].encode('utf8')

    with gzip.open('/tmp/file.txt.gz', 'wb') as f:
        f.write(content)

    with gzip.open('/tmp/file.txt.gz', 'rb') as f:
        file_content = f.read().decode('utf8')

    print(f"file_content: {file_content}")

    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {},
        "multiValueHeaders": {},
        "body": json.dumps({"statusCode": 200, "body": file_content})
    }


def payload_generator():

    random_size = random.randrange(999999)
    random_content = "".join( [random.choice(string.digits + string.ascii_letters) for i in range(random_size)] )

    return { "content":  random_content}
