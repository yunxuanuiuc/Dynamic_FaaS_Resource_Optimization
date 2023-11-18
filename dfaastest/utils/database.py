import psycopg2
from datetime import datetime
import json


class DB(object):

    def __init__(self, **params):
        self.postgres = psycopg2.connect(host=params['host'], dbname=params['db'], user=params['user'], password=params['password'])

    def query(self, sql, params):
        with self.postgres.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def insert(self, data):
        with self.postgres.cursor() as cursor:
            request_id = data["request_id"]
            payload = data["payload"]

            sql = """
                INSERT INTO logs_processor_data (request_id, payload, created_date, status)
                VALUES (%s, %s::json, CURRENT_TIMESTAMP, NULL)
            """

            cursor.execute(sql, (request_id, payload))

            self.postgres.commit()

    def update_record_status(self, request_id, status, experiment_id):
        with self.postgres.cursor() as cursor:
            cursor.execute(
                'UPDATE logs_processor_data SET status = %s, experiment_id = %s WHERE request_id = %s',
                (status, experiment_id, request_id)
            )

            self.postgres.commit()

    def insert_recommendation_probability(self, function_name, experiment_id, probability,
                                          num_of_records_observed, payload_size, recommended_size, current_memory):
        probability_dict_for_print = {};
        for key, value in probability.items():
            probability_dict_for_print[key] = '{:.4f}'.format(round(value, 4))

        with self.postgres.cursor() as cursor:
            cursor.execute(
                '''INSERT INTO recommendation_record (function_name, experiment_id, probability, records_observed, 
                recorded_date, payload_size, recommended_size, current_memory) 
                VALUES (%s, %s, %s::json, %s, %s, %s, %s, %s)''',
                (function_name, experiment_id, json.dumps(probability_dict_for_print), num_of_records_observed,
                 datetime.today().strftime('%F %T.%f')[:-3], payload_size, recommended_size, current_memory)
            )

            self.postgres.commit()