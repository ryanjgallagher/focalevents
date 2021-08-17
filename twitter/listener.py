import os
import sys
import time
import json
import yaml
import signal
import psycopg2
from pprint import pprint
from .helper import *

date_format = '%Y-%m-%dT%H:%M:%SZ'

class APIListener():
    """

    """
    def __init__(self,
                 event,
                 query_type,
                 config_f,
                 append,
                 verbose,
                 update_interval):
        self.event = event
        self.query_type = query_type

        self.verbose = verbose
        self.stop = False
        self.pause = False
        self.temp_unavail = False
        self.update_interval_mins = update_interval
        self.update_interval_secs = update_interval * 60

        # Config
        with open(config_f) as fin:
            config = yaml.load(fin, Loader=yaml.Loader)
        self.config = config

        # API keys
        self.api_key = config['keys']['twitter']['api_key']
        self.secret_key = config['keys']['twitter']['api_secret_key']
        self.bearer_token = config['keys']['twitter']['bearer_token']
        self.headers = {"Authorization": f"Bearer {self.bearer_token}"}

        # JSON output
        self.out_json_dir = config['output']['json']['twitter'][query_type]
        self.out_json_fname = f"{self.out_json_dir}/{event}.json"
        if append:
            self.write_mode = 'a+'
        else:
            self.write_mode = 'w+'
        # Database output
        db_user = config['psql']['user']
        database = config['psql']['database']
        schema = config['output']['psql']['twitter']['schema']
        tables = config['output']['psql']['twitter']['tables']
        self.tables = dict()
        self.tables['tweets'] = f"{schema}.{tables['tweets']}"
        self.tables['users'] = f"{schema}.{tables['users']}"
        self.tables['media'] = f"{schema}.{tables['media']}"
        self.tables['places'] = f"{schema}.{tables['places']}"

        # Database connection
        self.conn = psycopg2.connect(host=config['psql']['host'],
                                     port=config['psql']['port'],
                                     user=config['psql']['user'],
                                     database=config['psql']['database'],
                                     password=config['psql']['password'])
        self.conn.autocommit = True
        self.cur = self.conn.cursor()
        self.cur.execute("SET TIME ZONE 'UTC';")

        # Fields
        request_fields = config['request_fields']['twitter']
        self.request_fields = {"tweet.fields": ",".join(request_fields['tweets']),
                               "user.fields": ",".join(request_fields['users']),
                               "media.fields": ",".join(request_fields['media']),
                               "place.fields": ",".join(request_fields['places']),
                               "expansions": ",".join(config['expansions'])}
        # Insert commmands
        self.templates = dict()
        self.insert_cmds = dict()
        self.insert_fields = dict()
        for insert_type in ['tweets', 'users', 'media', 'places']:
            try:
                update_fields = config['update_fields']['twitter'][insert_type]
            except KeyError:
                update_fields = None
            insert_fields = set(config['insert_fields']['twitter'][insert_type].keys())
            self.insert_fields[insert_type] = insert_fields
            table = self.tables[insert_type]

            update_cmd = get_update_cmd(update_fields, self.query_type)
            insert_cmd,template = get_insert_cmd(insert_fields, table, update_cmd)
            self.insert_cmds[insert_type] = insert_cmd
            self.templates[insert_type] = template

            if insert_type == 'tweets':
                ref_insert_cmd,_ = get_insert_cmd(insert_fields, table)
                self.templates['ref'] = template
                self.insert_cmds['ref'] = ref_insert_cmd
                self.insert_fields['ref'] = insert_fields

        # Params of request
        self.params = dict()

        # Tweet counters
        now = time.time()
        self.n_tweets_total = 0
        self.n_tweets_last_15mins = 0
        self.n_tweets_since_update = 0
        self.prev_15min_time_mark = now
        self.prev_update_time_mark = now
        self.rate_limit = None
        self.n_calls_last_15mins = None

        if self.verbose:
            now = datetime.now().strftime("%Y-%m-%d %I:%M%p")
            print(f"Starting listener at {now}")
            print(f"Event: {self.event}")


    def exit_handler(self, signum, frame):
        """
        Helper function for handling CTRL+C exit, used with signal.SIGINT
        """
        self.stop = True
        if self.verbose:
            print('\nStopping...')


    def check_response_exception(self, response):
        """
        Checks to see if the status code returned by a response is valid. If
        not, then it raises an exception with a given message

        Parameters
        ----------
        response: obj
            A response object from a request made via the requests library
        """
        if not response.ok:
            if response.status_code == 503:
                self.temp_unavail = True
                if self.verbose:
                    print('\nAPI service is temporarily unavailable')
            elif response.status_code == 429:
                self.pause = True
                if self.verbose:
                    print('\nAPI says you are over the rate limit')
            else:
                status_text = response.text
                status_code = response.status_code
                raise Exception(f"Error in search (HTTP {status_code}): {status_text}")


    def check_rate_limit(self):
        """
        Checks if the query has exceeded the rate limit or the service is
        temporarily unavailable. If so, pauses search. Also handles printing
        out regular updates
        """
        update_reset = False
        unavail_reset = False
        rate_limit_reset = False

        # Check if listener needs to pause or print update
        now = time.time()
        secs_since_prev_15mins = now - self.prev_15min_time_mark
        secs_since_last_update = now - self.prev_update_time_mark
        if (self.n_calls_last_15mins >= self.rate_limit) or self.pause:
            n_sleep_secs = 900 - secs_since_prev_15mins + 15 # add a little extra
            if self.verbose:
                print('Stopping for {} mins'.format(round(n_sleep_secs/60)))
                print(f"Previous 15 min mark: {self.prev_15min_time_mark}")
                print(f"Seconds since last 15 min mark: {secs_since_prev_15mins}")
                print(f"Calls since last 15 min mark: {self.n_calls_last_15mins}")
            time.sleep(n_sleep_secs)
            rate_limit_reset = True
            update_reset = True
        elif 900 - secs_since_prev_15mins < 0:
            rate_limit_reset = True
            update_reset = True
        elif self.temp_unavail:
            if self.verbose:
                print('Stopping for 30 seconds')
            time.sleep(30)
            unavail_reset = True
        elif secs_since_last_update > self.update_interval_secs:
            update_reset = True

        # Reset status to keep listener running, and print update
        if rate_limit_reset or update_reset:
            if rate_limit_reset:
                n_tweets = self.n_tweets_last_15mins
                n_mins = 15
                self.n_calls_last_15mins = 0
                self.n_tweets_last_15mins = 0
                self.prev_15min_time_mark = now
                self.pause = False
            if update_reset:
                if update_reset and not rate_limit_reset:
                    n_tweets = self.n_tweets_since_update
                    n_mins = round(secs_since_last_update/60)
                self.n_tweets_since_update = 0
                self.prev_update_time_mark = now
            if self.verbose:
                self.print_update(n_tweets, n_mins)
        if unavail_reset:
            self.temp_unavail = False


    def limit_rate(self):
        """
        Makes listener sleep based on how much time is left in the 15 minute
        interval and how many calls have been made

        Time to sleep = # secs remaining / # calls remaining to be made
        """
        now = time.time()
        secs_since_prev_15mins = now - self.prev_15min_time_mark
        n_secs_remaining = 900 - secs_since_prev_15mins
        n_calls_remaining = self.rate_limit - self.n_calls_last_15mins
        if n_secs_remaining > 0 and n_calls_remaining > 0:
            n_sleep_secs = n_secs_remaining / n_calls_remaining
            if self.query_type == 'search':
                # Full archive search has minimum 1 request / sec limit too
                n_sleep_secs = max(1, n_sleep_secs)
            time.sleep(n_sleep_secs)
        elif n_secs_remaining > 0 and n_calls_remaining <= 0:
            self.pause = True


    def manage_writing(self, response_json):
        """
        Coordinates the writing of data, namely handling exceptions and updating
        the count of data returned from the API

        Parameters
        ----------
        response_json: dict
            JSON from an API response produced via the response library
        """
        try:
            if self.query_type == 'stream':
                tweets = [response_json['data']]
            else:
                tweets = response_json['data']
            includes = response_json['includes']
            self.write(tweets, includes)

            self.n_tweets_total += len(tweets)
            self.n_tweets_since_update += len(tweets)
            self.n_tweets_last_15mins += len(tweets)
        except KeyError as err:
            if 'meta' in response_json and 'result_count' in response_json['meta']:
                if response_json['meta']['result_count'] == 0:
                    pass
                else:
                    pprint(response_json)
                    raise err
            else:
                pprint(response_json)
                raise err


    def write(self, tweets, includes):
        """
        Writes data to a PostgreSQL database and a newline-delimited JSON file.
        All raw data is written to the JSON file. Insertion data is retrieved
        for all tweets, referenced tweets, users, media, and places and inserted
        into the database. The insertion subsets to the fields specified by the
        config file (`insert_fields.platform`)

        Parameters
        -----------
        tweets: list of dicts
            List of dictionary tweet objects. The return of the `data` field
            from the API. Note: for the stream, we manually wrap it in a list
            because only a single tweet is returned
        includes: dict of dicts
            Dictionary of different referenced objects that were included. The
            return of the `includes` field from the API
        """
        all_inserts = get_all_inserts(tweets, includes, self.event, self.query_type)

        # Write to database
        insert_types = ['tweets', 'ref', 'users', 'media', 'places']
        for insert_type,inserts in zip(insert_types, all_inserts):
            # Subset to insert fields
            # TODO: this is not efficient to do this every time
            insert_fields = self.insert_fields[insert_type]
            for insert in inserts:
                for k in list(insert.keys()):
                    if k not in insert_fields:
                        del insert[k]

            # Insert
            template = self.templates[insert_type]
            insert_cmd = self.insert_cmds[insert_type]

            try:
                psycopg2.extras.execute_values(self.cur,
                                               sql=insert_cmd,
                                               argslist=inserts,
                                               template=template)
            except Exception as e:
                print(f"Failed insert: {insert_type}\n")
                pprint(inserts)
                print()
                print(f"Insert command\n{insert_cmd}\n")
                print(f"Template\n{template}\n")
                raise e

        # Write to JSON
        for tweet in tweets:
            out_str = json.dumps(tweet)
            self.out_json_f.write(f"{out_str}\n")


    def print_update(self, n_tweets, n_mins):
        """
        Prints out the number of tweets that have been retrieved from the API
        since the last update

        Note: this undercounts the number of tweets that are inserted because
        it does not count referenced tweets that have been inserted

        Parameters
        ----------
        n_tweets: int
            The number of tweets since the last update
        n_mins:
            The number of minutes since the last update
        """
        print('\n\t'+datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        out_str = f"\t{n_tweets:,} tweets in the last {n_mins} mins"
        out_str = f"{out_str} | {self.n_tweets_total:,} tweets total"
        print(out_str)
