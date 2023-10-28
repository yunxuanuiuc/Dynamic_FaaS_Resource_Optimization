import boto3

# Create a Lambda client
client = boto3.client('lambda')

# Call the update_function_configuration method
response = client.update_function_configuration(
    FunctionName='my-function',
    MemorySize=512
)
