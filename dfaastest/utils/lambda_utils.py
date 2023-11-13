import json
import logging
import os
import time

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

def create(lambda_config):
    """
    Shows how to deploy an AWS Lambda function, create a REST API, call the REST API
    in various ways, and remove all of the resources after the demo completes.
    """
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # LAMBDA CONFIG VARIABLES
    lambda_filename = lambda_config['filename']
    lambda_zipfilename = lambda_config['zipfilename']
    lambda_handler_name = lambda_config['handler_name']
    lambda_role_name = lambda_config['role_name']
    lambda_function_name = lambda_config['function_name']
    lambda_description = lambda_config['description']
    lambda_runtime = lambda_config['runtime']
    api_name = lambda_config['api_name']
    api_base_path = lambda_config['api_base_path']
    api_stage = lambda_config['api_stage']

    iam_resource = boto3.resource('iam')
    lambda_client = boto3.client('lambda')
    wrapper = LambdaWrapper(lambda_client, iam_resource)
    apig_client = boto3.client('apigateway')

    print("Checking for IAM role for Lambda...")
    iam_role, should_wait = wrapper.create_iam_role_for_lambda(lambda_role_name)

    print(f"Creating AWS Lambda function {lambda_function_name} from "
          f"{lambda_handler_name}...")
    deployment_package = wrapper.create_deployment_package(
        lambda_filename, lambda_zipfilename, libraries='')

    # CA
    existing_function = wrapper.get_function(lambda_function_name)

    if not existing_function:
        print(f"Creating new function...")
        lambda_function_arn = wrapper.create_function(
            lambda_function_name, lambda_handler_name, iam_role, deployment_package, lambda_description, lambda_runtime)
    else:
        print(f"Updating existing function...")
        lambda_function_arn = existing_function['Configuration']['FunctionArn']

        wrapper.update_function_code(lambda_function_name, deployment_package)
        wrapper.wait_for_update(lambda_function_name)

        wrapper.update_function_configuration(lambda_function_name, lambda_handler_name)
        wrapper.wait_for_update(lambda_function_name)

    existing_rest_api = get_rest_api(api_name)
    print(f"existing_rest_api: {existing_rest_api}")

    if not existing_rest_api:
        print(f"Creating Amazon API Gateway REST API {api_name}...")
        account_id = boto3.client('sts').get_caller_identity()['Account']
        api_id = create_rest_api(
            apig_client, api_name, api_base_path, api_stage, account_id,
            lambda_client, lambda_function_arn)
    else:
        api_id = existing_rest_api['id']

    api_url = construct_api_url(
        api_id, apig_client.meta.region_name, api_stage, api_base_path)
    print(f"REST API URL is:\n\t{api_url}")
    print(f"Sleeping for a couple seconds to give AWS time to prepare...")
    time.sleep(2)


def get_region_name():
    apig_client = boto3.client('apigateway')
    return apig_client.meta.region_name


def create_rest_api(
        apigateway_client, api_name, api_base_path, api_stage,
        account_id, lambda_client, lambda_function_arn):
    """
    Creates a REST API in Amazon API Gateway. The REST API is backed by the specified
    AWS Lambda function.

    The following is how the function puts the pieces together, in order:
    1. Creates a REST API in Amazon API Gateway.
    2. Creates a '/demoapi' resource in the REST API.
    3. Creates a method that accepts all HTTP actions and passes them through to
       the specified AWS Lambda function.
    4. Deploys the REST API to Amazon API Gateway.
    5. Adds a resource policy to the AWS Lambda function that grants permission
       to let Amazon API Gateway call the AWS Lambda function.

    :param apigateway_client: The Boto3 Amazon API Gateway client object.
    :param api_name: The name of the REST API.
    :param api_base_path: The base path part of the REST API URL.
    :param api_stage: The deployment stage of the REST API.
    :param account_id: The ID of the owning AWS account.
    :param lambda_client: The Boto3 AWS Lambda client object.
    :param lambda_function_arn: The Amazon Resource Name (ARN) of the AWS Lambda
                                function that is called by Amazon API Gateway to
                                handle REST requests.
    :return: The ID of the REST API. This ID is required by most Amazon API Gateway
             methods.
    """
    try:
        response = apigateway_client.create_rest_api(name=api_name)
        api_id = response['id']
        logger.info("Create REST API %s with ID %s.", api_name, api_id)
    except ClientError:
        logger.exception("Couldn't create REST API %s.", api_name)
        raise

    try:
        response = apigateway_client.get_resources(restApiId=api_id)
        root_id = next(item['id'] for item in response['items'] if item['path'] == '/')
        logger.info("Found root resource of the REST API with ID %s.", root_id)
    except ClientError:
        logger.exception("Couldn't get the ID of the root resource of the REST API.")
        raise

    try:
        response = apigateway_client.create_resource(
            restApiId=api_id, parentId=root_id, pathPart=api_base_path)
        base_id = response['id']
        logger.info("Created base path %s with ID %s.", api_base_path, base_id)
    except ClientError:
        logger.exception("Couldn't create a base path for %s.", api_base_path)
        raise

    try:
        apigateway_client.put_method(
            restApiId=api_id, resourceId=base_id, httpMethod='ANY',
            authorizationType='NONE')
        logger.info("Created a method that accepts all HTTP verbs for the base "
                    "resource.")
    except ClientError:
        logger.exception("Couldn't create a method for the base resource.")
        raise

    lambda_uri = \
        f'arn:aws:apigateway:{apigateway_client.meta.region_name}:' \
        f'lambda:path/2015-03-31/functions/{lambda_function_arn}/invocations'
    try:
        # NOTE: You must specify 'POST' for integrationHttpMethod or this will not work.
        apigateway_client.put_integration(
            restApiId=api_id, resourceId=base_id, httpMethod='ANY', type='AWS_PROXY',
            integrationHttpMethod='POST', uri=lambda_uri)
        logger.info(
            "Set function %s as integration destination for the base resource.",
            lambda_function_arn)
    except ClientError:
        logger.exception(
            "Couldn't set function %s as integration destination.", lambda_function_arn)
        raise

    try:
        apigateway_client.create_deployment(restApiId=api_id, stageName=api_stage)
        logger.info("Deployed REST API %s.", api_id)
    except ClientError:
        logger.exception("Couldn't deploy REST API %s.", api_id)
        raise

    source_arn = \
        f'arn:aws:execute-api:{apigateway_client.meta.region_name}:' \
        f'{account_id}:{api_id}/*/*/{api_base_path}'
    try:
        lambda_client.add_permission(
            FunctionName=lambda_function_arn, StatementId=f'Statement-ID-{int(time.time())}',
            Action='lambda:InvokeFunction', Principal='apigateway.amazonaws.com',
            SourceArn=source_arn)
        logger.info("Granted permission to let Amazon API Gateway invoke function %s "
                    "from %s.", lambda_function_arn, source_arn)
    except ClientError:
        logger.exception("Couldn't add permission to let Amazon API Gateway invoke %s.",
                         lambda_function_arn)
        raise

    return api_id


def get_rest_api(rest_api_name):
    apig_client = boto3.client('apigateway')

    rest_apis = apig_client.get_rest_apis()['items']

    for api in rest_apis :
        #print(f"api['name']: {api['name']}")

        if api['name'] == rest_api_name:
            return api

    return None


def construct_api_url(api_id, region, api_stage, api_base_path):
    """
    Constructs the URL of the REST API.

    :param api_id: The ID of the REST API.
    :param region: The AWS Region where the REST API was created.
    :param api_stage: The deployment stage of the REST API.
    :param api_base_path: The base path part of the REST API.
    :return: The full URL of the REST API.
    """
    api_url = \
        f'https://{api_id}.execute-api.{region}.amazonaws.com/' \
        f'{api_stage}/{api_base_path}'
    logger.info("Constructed REST API base URL: %s.", api_url)
    return api_url


def update_memory(funk_name, memory):
    try:
        lambda_client = boto3.client('lambda')
        lambda_client.update_function_configuration(FunctionName=funk_name, MemorySize=memory)
    except Exception as e:
        print(f"Error occurred while updating the function {funk_name} memory to {memory} - error: {e}")
        raise e


# snippet-start:[python.example_code.python.LambdaWrapper.full]
# snippet-start:[python.example_code.python.LambdaWrapper.decl]
class LambdaWrapper:
    def __init__(self, lambda_client, iam_resource):
        self.lambda_client = lambda_client
        self.iam_resource = iam_resource
    # snippet-end:[python.example_code.python.LambdaWrapper.decl]

    @staticmethod
    def create_deployment_package(source_file, destination_file, libraries):
        """
        Creates a Lambda deployment package in .zip format in an in-memory buffer. This
        buffer can be passed directly to Lambda when creating the function.

        :param source_file: The name of the file that contains the Lambda handler
                            function.
        :param destination_file: The name to give the file when it's deployed to Lambda.
        :return: The deployment package.
        """
        os.system(f"rm {destination_file}")
        os.system(f"zip -r {destination_file} {source_file} {' '.join(libraries)}")

        with open(destination_file, 'rb') as file_data:
            buffer = file_data.read()

        return buffer

    def get_iam_role(self, iam_role_name):
        """
        Get an AWS Identity and Access Management (IAM) role.

        :param iam_role_name: The name of the role to retrieve.
        :return: The IAM role.
        """
        role = None
        try:
            temp_role = self.iam_resource.Role(iam_role_name)
            temp_role.load()
            role = temp_role
            logger.info("Got IAM role %s", role.name)
        except ClientError as err:
            if err.response['Error']['Code'] == 'NoSuchEntity':
                logger.info("IAM role %s does not exist.", iam_role_name)
            else:
                logger.error(
                    "Couldn't get IAM role %s. Here's why: %s: %s", iam_role_name,
                    err.response['Error']['Code'], err.response['Error']['Message'])
                raise
        return role

    def create_iam_role_for_lambda(self, iam_role_name):
        """
        Creates an IAM role that grants the Lambda function basic permissions. If a
        role with the specified name already exists, it is used for the demo.

        :param iam_role_name: The name of the role to create.
        :return: The role and a value that indicates whether the role is newly created.
        """
        role = self.get_iam_role(iam_role_name)
        if role is not None:
            return role, False

        else:
            raise NotImplementedError

        # lambda_assume_role_policy = {
        #     'Version': '2012-10-17',
        #     'Statement': [
        #         {
        #             'Effect': 'Allow',
        #             'Principal': {
        #                 'Service': 'lambda.amazonaws.com'
        #             },
        #             'Action': 'sts:AssumeRole'
        #         }
        #     ]
        # }
        # policy_arn = 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        #
        # try:
        #     role = self.iam_resource.create_role(
        #         RoleName=iam_role_name,
        #         AssumeRolePolicyDocument=json.dumps(lambda_assume_role_policy))
        #     logger.info("Created role %s.", role.name)
        #     role.attach_policy(PolicyArn=policy_arn)
        #     logger.info("Attached basic execution policy to role %s.", role.name)
        # except ClientError as error:
        #     if error.response['Error']['Code'] == 'EntityAlreadyExists':
        #         role = self.iam_resource.Role(iam_role_name)
        #         logger.warning("The role %s already exists. Using it.", iam_role_name)
        #     else:
        #         logger.exception(
        #             "Couldn't create role %s or attach policy %s.",
        #             iam_role_name, policy_arn)
        #         raise
        #
        # return role, True

    # snippet-start:[python.example_code.lambda.GetFunction]
    def get_function(self, function_name):
        """
        Gets data about a Lambda function.

        :param function_name: The name of the function.
        :return: The function data.
        """
        response = None
        try:
            response = self.lambda_client.get_function(FunctionName=function_name)
        except ClientError as err:
            if err.response['Error']['Code'] == 'ResourceNotFoundException':
                logger.info("Function %s does not exist.", function_name)
            else:
                logger.error(
                    "Couldn't get function %s. Here's why: %s: %s", function_name,
                    err.response['Error']['Code'], err.response['Error']['Message'])
                raise
        return response
    # snippet-end:[python.example_code.lambda.GetFunction]

    # snippet-start:[python.example_code.lambda.CreateFunction]
    def create_function(self, function_name, handler_name, iam_role, deployment_package, description, runtime):
        """
        Deploys a Lambda function.

        :param function_name: The name of the Lambda function.
        :param handler_name: The fully qualified name of the handler function. This
                             must include the file name and the function name.
        :param iam_role: The IAM role to use for the function.
        :param deployment_package: The deployment package that contains the function
                                   code in .zip format.
        :return: The Amazon Resource Name (ARN) of the newly created function.
        """
        try:
            response = self.lambda_client.create_function(
                FunctionName=function_name,
                Description=description,
                Runtime=runtime,
                Role=iam_role.arn,
                Handler=handler_name,
                Code={'ZipFile': deployment_package},
                Publish=True)
            function_arn = response['FunctionArn']
            waiter = self.lambda_client.get_waiter('function_active_v2')
            waiter.wait(FunctionName=function_name)
            logger.info("Created function '%s' with ARN: '%s'.",
                        function_name, response['FunctionArn'])
        except ClientError:
            logger.error("Couldn't create function %s.", function_name)
            raise
        else:
            return function_arn
    # snippet-end:[python.example_code.lambda.CreateFunction]

    # snippet-start:[python.example_code.lambda.DeleteFunction]
    def delete_function(self, function_name):
        """
        Deletes a Lambda function.

        :param function_name: The name of the function to delete.
        """
        try:
            self.lambda_client.delete_function(FunctionName=function_name)
        except ClientError:
            logger.exception("Couldn't delete function %s.", function_name)
            raise
    # snippet-end:[python.example_code.lambda.DeleteFunction]

    # snippet-start:[python.example_code.lambda.Invoke]
    def invoke_function(self, function_name, function_params, get_log=False):
        """
        Invokes a Lambda function.

        :param function_name: The name of the function to invoke.
        :param function_params: The parameters of the function as a dict. This dict
                                is serialized to JSON before it is sent to Lambda.
        :param get_log: When true, the last 4 KB of the execution log are included in
                        the response.
        :return: The response from the function invocation.
        """
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps(function_params),
                LogType='Tail' if get_log else 'None')
            logger.info("Invoked function %s.", function_name)
        except ClientError:
            logger.exception("Couldn't invoke function %s.", function_name)
            raise
        return response
    # snippet-end:[python.example_code.lambda.Invoke]

    # snippet-start:[python.example_code.lambda.UpdateFunctionCode]
    def update_function_code(self, function_name, deployment_package):
        """
        Updates the code for a Lambda function by submitting a .zip archive that contains
        the code for the function.

        :param function_name: The name of the function to update.
        :param deployment_package: The function code to update, packaged as bytes in
                                   .zip format.
        :return: Data about the update, including the status.
        """
        try:
            response = self.lambda_client.update_function_code(
                FunctionName=function_name, ZipFile=deployment_package, Publish=True)
            print(f"update_function_code - response: {response}")
        except ClientError as err:
            logger.error(
                "Couldn't update function %s. Here's why: %s: %s", function_name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
        else:
            return response
    # snippet-end:[python.example_code.lambda.UpdateFunctionCode]

    # snippet-start:[python.example_code.lambda.UpdateFunctionConfiguration]
    def update_function_configuration(self, function_name, handler):
        """
        Updates the environment variables for a Lambda function.

        :param function_name: The name of the function to update.
        :return: Data about the update, including the status.
        """
        try:
            response = self.lambda_client.update_function_configuration(
                FunctionName=function_name, Handler=handler)
            print(f"update_function_configuration - response - update_function_configuration")
        except ClientError as err:
            logger.error(
                "Couldn't update function configuration %s. Here's why: %s: %s", function_name,
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise
        else:
            return response
    # snippet-end:[python.example_code.lambda.UpdateFunctionConfiguration]

    # snippet-start:[python.example_code.lambda.ListFunctions]
    def list_functions(self):
        """
        Lists the Lambda functions for the current account.
        """
        try:
            func_paginator = self.lambda_client.get_paginator('list_functions')
            for func_page in func_paginator.paginate():
                for func in func_page['Functions']:
                    print(func['FunctionName'])
                    desc = func.get('Description')
                    if desc:
                        print(f"\t{desc}")
                    print(f"\t{func['Runtime']}: {func['Handler']}")
        except ClientError as err:
            logger.error(
                "Couldn't list functions. Here's why: %s: %s",
                err.response['Error']['Code'], err.response['Error']['Message'])
            raise

    def wait_for_update(self, lambda_function_name):
        wait_for_update_to_complete = True
        while wait_for_update_to_complete:
            existing_function = self.get_function(lambda_function_name)
            wait_for_update_to_complete = existing_function['Configuration']['LastUpdateStatus'] == 'InProgress'
            time.sleep(1)


# if __name__ == '__main__':
#     get_rest_api("dfaastest-decompress-rest-api")
