import argparse
import logging
import os
import time
import yaml

import boto3
from botocore.exceptions import ClientError

from utils.config_utils import get_funk_names, get_config
from utils.lambda_utils import create

logger = logging.getLogger(__name__)


class FunkGen(object):

    def __init__(self):
        self.lambda_config = ''

    def create(self, funk_name):
        config = get_config()
        funk_config = config['funk_generator'][funk_name]
        create(funk_config)


if __name__ == '__main__':

    funk_names = get_funk_names()

    parser = argparse.ArgumentParser(description='Function generator program, creates/updates lambda functions.')
    parser.add_argument('--action', choices=['create'], help='Create (or update) lambda function')
    parser.add_argument('--funk-name', choices=funk_names, help='Function name for the action')

    args = parser.parse_args()
    print(f'args: {args}')
    print(f'args.funk_name: {args.funk_name}')

    funk_gen = FunkGen()

    match args.action:
        case 'create':
            funk_gen.create(args.funk_name)
