import os
import sys
import time
import json
import yaml
import queue
import signal
import argparse
import requests
import dateutil
import psycopg2
import numpy as np
from pprint import pprint
from datetime import datetime
from psycopg2.extras import Json
from multiprocessing import Queue
from multiprocessing import Value
from multiprocessing import Process
from .helper import *
from .listener import APIListener


class StreamListener(APIListener):
    """
    For connecting to the Twitter API v2 filter stream and writing out the data

    Parameters
    ----------
    event: str
        The name of the streaming event. This should be a unique name that can
        be used as an identifier for the set of tweets that result from this
        stream. There must be a corresponding rules configuration file with the
        same event name
    config_f: str
        The configuration file to use
    delete_existing_rules: boolean
        Whether to delete rules that have already been set through the Twitter
        API for a previous stream. If False, then adds rules to those already
        on the stream
    append: bool
        Whether to append to the JSON file. If False, then overwrites any JSON
        file with the same name that already exists
    verbose: bool
        Whether to print out information/updates of the search. Defaults to True
    update_interval: int
        How often to print updates of the number of tweets collected, in minutes
    n_mins_timeout: int
        How many minutes before the writing queue times out from not receiving
        any data
    dry_run: bool
        Whether to run a "dry run" of the rules without connnecting to the
        Twitter stream to make sure that the query rules are syntactically valid
    """
    def __init__(self,
                 event,
                 config_f,
                 delete_existing_rules,
                 append,
                 verbose,
                 update_interval,
                 n_mins_timeout):
        super().__init__(
            event=event,
            query_type='stream',
            config_f=config_f,
            append=append,
            verbose=verbose,
            update_interval=update_interval
        )
        self.rate_limit = np.inf
        self.n_calls_last_15mins = -1 * np.inf

        self.rules_endpoint = self.config['endpoints']['twitter']['rules']
        self.stream_endpoint = self.config['endpoints']['twitter']['stream']

        # Filter rules
        self.delete_existing_rules = delete_existing_rules
        self.rules_f = f"{self.config['input']['twitter']['stream']}/{self.event}.yaml"
        with open(self.rules_f) as fin:
            self.rules = yaml.load(fin, Loader=yaml.Loader)['rules']
        self.params = self.request_fields

        # Separate computing process for writing tweets
        self.n_secs_timeout = 60 * n_mins_timeout
        self.write_queue = Queue()
        self.writer = Process(target=self.manage_writing, daemon=True)

        self.out_json_f = open(self.out_json_fname, self.write_mode)


    def get_rules(self):
        """
        Gets all the existing rules that are being used to filter the stream

        Returns
        -------
        rules: dict
            Dictionary where the key "data" holds a list of dictionaries, each
            with the keys, "value" (the rule), "tag" (the description), and
            "id". Also contains the fields "meta" of when request was made, and
            "summary", which holds a dictionary of how many rules were "created"
            and "not_created", and how many were "valid" and "invalid"
        """
        response = requests.get(self.rules_endpoint, headers=self.headers)
        self.check_response_exception(response)
        if 'data' in response.json():
            self.api_rules_response = response.json()
        else:
            self.api_rules_response = None


    def delete_rules(self):
        """
        Deletes rules that are already being used to filter the stream
        """
        self.get_rules()
        if self.api_rules_response is None or "data" not in self.api_rules_response:
            return

        rule_ids = list(map(lambda r: r["id"], self.api_rules_response["data"]))
        to_delete = {"delete": {"ids": rule_ids}}
        response = requests.post(self.rules_endpoint, headers=self.headers,
                                 json=to_delete)
        self.check_response_exception(response)
        # Make sure api_rules_response is updated
        self.get_rules()


    def set_rules(self):
        """
        Sets stream rules for the event. Deletes existing rules if specified
        """
        if self.delete_existing_rules:
            self.delete_rules()

        to_add = {"add": self.rules}
        response = requests.post(self.rules_endpoint, headers=self.headers,
                                 json=to_add)
        self.check_response_exception(response)
        # Make sure api_rules_response is updated
        self.get_rules()


    def stream(self):
        """
        Connects to the Twitter filter stream and writes out the returned data
        to both a JSON file and a Postgres database.
        """
        self.writer.start()

        # Wait to set this until here, otherwise it sets it for both processes
        # and we only want this exit handler for the main thread
        signal.signal(signal.SIGINT, self.exit_handler)

        # Connect to stream
        response = requests.get(self.stream_endpoint, headers=self.headers,
                                params=self.params, stream=True)
        self.check_response_exception(response)
        if self.verbose:
            print('Connected to the filter stream')
            print('Streaming tweets...')

        # Read tweets and put them on queue to write
        # Note: if a small number of tweets are coming in, then the stream will
        # not stop after CTRL+c until the next tweet comes in. Until then, the
        # process is caught up in response.iter_lines()
        for response_line in response.iter_lines():
            if response_line:
                self.check_rate_limit()

                response_json = json.loads(response_line)
                self.check_response_exception(response)
                if self.pause or self.temp_unavail:
                    continue
                self.write_queue.put((response_json, self.stop))

                self.n_tweets_total += 1
                self.n_tweets_since_update += 1

                if self.stop:
                    return


    def manage_writing(self):
        """
        Retrieves data from the writing queue and writes it. Handles keyboard
        except for a CTRL+C exit
        """
        try:
            while True:
                try:
                    response_json,stop = self.write_queue.get(timeout=self.n_secs_timeout)
                except queue.Empty:
                    # TODO: even if this times out, the main thread doesn't
                    # end because it's caught waiting for something from iter_lines()
                    # and it never reaches `stop`. Also `stop` isn't even
                    # shared between the main process and the writing process
                    print("Stream timed out. Ending the stream")
                    self.stop = True

                if self.stop:
                    return

                super().manage_writing(response_json)

        except KeyboardInterrupt:
            if self.verbose:
                print("\n\tFinishing writing...")
            while not self.write_queue.empty():
                tweets = [response_json['data']]
                includes = response_json['includes']
                self.write_tweets(tweets, includes)
            if self.verbose:
                print("\tFinished writing remainder of queue")


# ------------------------------------------------------------------------------
# --------------------------- End of class definition --------------------------
# ------------------------------------------------------------------------------
def main(event, delete_rules, config_f, append, verbose, update_interval,
         n_mins_timeout, dry_run):
    """
    Listens to the Twitter API v2 filter stream. First, it sets the rules to
    filter by. It then connects to the stream. Finally, it handles joining the
    multiprocessing writing thread and, if applicable, closing any open writing
    files

    See above class definition for parameter explanations
    """
    # Connect to stream
    stream = StreamListener(event,
                            config_f=config_f,
                            delete_existing_rules=delete_rules,
                            append=append,
                            verbose=verbose,
                            update_interval=update_interval,
                            n_mins_timeout=n_mins_timeout)
    if dry_run:
        if stream.delete_existing_rules:
            stream.delete_rules()
        to_add = {"add": stream.rules}
        response = requests.post(stream.rules_endpoint, headers=stream.headers,
                                 json=to_add, params={'dry_run': True})
        print('Dry run results\n---------------')
        pprint(response.json())
        sys.exit()
    else:
        stream.set_rules()
        stream.stream()

        # Wait for the writing thread to finish and wrap up
        stream.writer.join()
        stream.out_json_f.close()
        stream.conn.commit()
        stream.cur.close()
        stream.conn.close()
        if verbose:
            print('\nClosed writing and committed changes to database')
            now = datetime.now().strftime("%Y-%m-%d %I:%m%p")
            print(f"\nStream finished at {now}")
            print(f"\n{stream.n_tweets_total:,} returned by the API\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Twitter filter stream")
    parser.add_argument("event", type=str)
    parser.add_argument("-config", type=str, default="config.yaml")
    parser.add_argument("-update_interval", type=int, default=15)
    parser.add_argument("-n_mins_timeout", type=int, default=15)
    # Booleans can't be parsed directly, so you set a flag for each option
    parser.add_argument("--delete_rules", dest="delete_rules", action="store_true")
    parser.add_argument("--update_rules", dest="delete_rules", action="store_false")
    parser.add_argument("--append", dest="append", action="store_true")
    parser.add_argument("--verbose", dest="verbose", action="store_true")
    parser.add_argument("--quiet", dest="verbose", action="store_false")
    parser.add_argument("--overwrite", dest="append", action="store_false")
    parser.add_argument("--dry_run", dest="dry_run", action="store_true")
    parser.set_defaults(delete_rules=True, append=True, dry_run=False)

    args = parser.parse_args()

    main(args.event,
         args.delete_rules,
         args.config,
         args.append,
         args.verbose,
         args.update_interval,
         args.n_mins_timeout,
         args.dry_run)
