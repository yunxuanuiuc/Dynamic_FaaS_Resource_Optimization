import argparse
import datetime
import time
import json

from funk_updater import FunkUpdater
from utils.config_utils import get_config, get_funk_names
from utils.database import DB
from cmab_client import CmabClient


class DfaastestOperator(object):

    def __init__(self, config, dryrun, funk_name, experiment_id):
        self.config = config
        self.dryrun = dryrun
        self.funk_name = funk_name
        self.experiment_id = experiment_id

        self.config['cmab_agent']['model_funk'] = self.funk_name
        self.config['cmab_agent']['model_experiment'] = self.experiment_id
        self.cmab_client = CmabClient(self.config['cmab_agent'])

        self.funk_updater = FunkUpdater(self.config['funk_generator'][funk_name])

        self.wait_period = config['operator']['wait_period']
        self.recommend_payload_algorithm = config['operator']['recommend_payload_algorithm']

        # connect to DB
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

    def start(self):
        print(f"DfaastestOperator starting...")

        self.run()

    def get_data(self):
        print(f"DfaastestOperator get_data...")

        if not self.dryrun:
            records = self.db.query(
                sql='''
            select *
              from logs_processor_data
             where status is null
               and function_name = %s
             order by created_date
             ''',
                params=(self.funk_name,)
            )

        else:
            # dryrun simulated sample record
            records = [
                (
                    '32cf8aaa-ae6e-4b11-93f8-370b8fc58bab',
                    'decompress',
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

    def get_last_x_records(self, limit=None):
        print(f"DfaastestOperator get_last_x_records...")

        if not self.dryrun:

            query = '''
            select *
              from logs_processor_data
             where function_name = %s
               and status is not null
             order by created_date desc
            '''

            if limit:
                query += f'''
                limit {limit}
                '''

            records = self.db.query(sql=query, params=(self.funk_name,))

        else:
            # dryrun simulated sample record
            records = [
                (
                    '32cf8aaa-ae6e-4b11-93f8-370b8fc58bab',
                    'decompress',
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

    def get_average_payload(self, records):
        if records:
            cumulative_payload = 0

            for record in records:
                print(f"get_average_payload - record: {record}")
                payload = record[2]
                cumulative_payload += int(payload["payload_size"])

            return cumulative_payload / len(records)
        else:
            return 1

    def run(self):
        print(f"DfaastestOperator running...")

        # To stop we need to kill the process
        while True:
            records = self.get_data()

            if records:

                # Step 1 Observe
                for record in records:
                    print(f"record: {record}")

                    self.cmab_client.send_observe(payload=record[2]) # 2 is the payload

                    self.db.update_record_status(record[0], 'P', self.experiment_id)

                # Step 2 Recommend
                payload_size = 1
                match self.recommend_payload_algorithm:
                    case 'wait_period':
                        payload_size = self.get_average_payload(records)

                    case 'last_10':
                        last_10_records = self.get_last_x_records(10)
                        payload_size = self.get_average_payload(last_10_records)

                    case 'last_100':
                        last_100_records = self.get_last_x_records(100)
                        payload_size = self.get_average_payload(last_100_records)

                recommendation = self.cmab_client.send_recommend(payload={"payload_size": payload_size})
                print(f"getting recommendation from cmab agent: {recommendation['recommended_memory']}")
                self.funk_updater.update_function_memory(memory=recommendation['recommended_memory'])
                self.cmab_client.probability = recommendation['action_probability']
                self.cmab_client.probability_dict = {self.cmab_client.mem_list[i]: recommendation['probability_list'][i] for i in range(len(self.cmab_client.mem_list))}
                self.db.insert_recommendation_probability(
                    self.funk_name, self.experiment_id, json.dumps(self.cmab_client.probability_dict), records[-1][2]["memory_size"]) # memory_size of last record

                if self.dryrun:
                    break

            else:
                time.sleep(self.wait_period)  # wait before checking again

                if self.dryrun:
                    break


if __name__ == '__main__':

    funk_names = get_funk_names()
    config = get_config()

    parser = argparse.ArgumentParser(description='Run the dfaastest operator for integration between the Logs Processor and CMAB agent.')
    parser.add_argument('--action', default="run", choices=['run', 'test'], help='Run operator continuously or do a test run')
    parser.add_argument('--dryrun', action='store_true', help='Whether or not to run continuously, read database, ie. run for realz.')
    parser.add_argument('--funk-name', required=True, choices=funk_names, help='Which function to operate?')
    parser.add_argument('--experiment-id', required=True, help='An experiment name or identifier to differentiate between experiment runs.')

    args = parser.parse_args()
    print(f'args: {args}')

    match args.action:
        case 'run':
            operator = DfaastestOperator(
                config=config,
                dryrun=args.dryrun,
                funk_name=args.funk_name,
                experiment_id=args.experiment_id
            )
            operator.start()

        case 'test':
            raise NotImplementedError
