import argparse
import datetime
import time

from utils.config_utils import get_config
from utils.database import DB
from cmab_client import CmabClient


class DfaastestOperator(object):

    def __init__(self, config, dryrun):
        self.config = config
        self.dryrun = dryrun

    def start(self):
        print(f"DfaastestOperator starting...")

        self.db_config = self.config['database']

        DB_HOST = self.db_config['host']
        DB_USER = self.db_config['user']
        DB_PASS = self.db_config['pass']
        DB_NAME = self.db_config['db_name']
        DB_TABLE = self.db_config['table']

        try:
            self.db = DB(host=DB_HOST, user=DB_USER, password=DB_PASS, db=DB_NAME)
        except Exception as e:
            print("ERROR: Unexpected error: Could not connect to the PostgreSQL instance.")
            raise e

        self.cmab_client = CmabClient(self.config)

        self.run()

    def get_data(self):
        print(f"DfaastestOperator get_data...")

        if not self.dryrun:
            records = self.db.query(sql='select * from logs_processor_data where status is null order by created_date', params=None)
        else:
            records = [
                (
                    '32cf8aaa-ae6e-4b11-93f8-370b8fc58bab',
                    {
                        'duration': '1.90',
                        'memory_size': '128',
                        'billed_duration': '2',
                        'max_memory_used': '37'
                    },
                    datetime.datetime(2023, 11, 1, 20, 4, 59, 515001),
                    None
                )
            ]

        print(f"DfaastestOperator.get_data - records: {records}")

        return records

    def run(self):
        print(f"DfaastestOperator running...")

        # To stop we need to kill the process
        while True:
            records = self.get_data()

            if records:

                for record in records:
                    print(f"record: {record}")

                    self.cmab_client.send_request(payload=record[1])

                    self.db.update_record_status(record[0], 'P')

                if self.dryrun:
                    break

            else:
                time.sleep(60 * 5)  # wait before checking again

                if self.dryrun:
                    break


if __name__ == '__main__':

    config = get_config()

    parser = argparse.ArgumentParser(description='Run the dfaastest operator for integration between the Logs Processor and CMAB agent.')
    parser.add_argument('--action', default="run", choices=['run', 'test'], help='Run operator continuously or do a test run')
    parser.add_argument('--dryrun', action='store_true', help='Whether or not to run continuously, read database, ie. run for realz.')

    args = parser.parse_args()
    print(f'args: {args}')

    match args.action:
        case 'run':
            operator = DfaastestOperator(config, args.dryrun)
            operator.start()

        case 'test':
            raise NotImplementedError
