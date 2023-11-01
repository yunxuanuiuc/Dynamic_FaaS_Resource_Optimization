import gzip
import json


def lambda_handler(event, context):

    content = b"Lots of content here"

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
        "body": json.dumps({"statusCode": 200,"body": file_content})
    }
