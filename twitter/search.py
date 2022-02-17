import json
import yaml
import signal
import argparse
import requests
import warnings
from queue import Queue
from pprint import pprint
from datetime import datetime
from datetime import timedelta
from dateutil import parser as dateparser
from .helper import *
from .listener import APIListener

date_format = '%Y-%m-%dT%H:%M:%SZ'


class SearchListener(APIListener):
    """
    Performs full historical archive searches of tweets. All searches are
    organized by an `event` name which connects various tweet data that are
    initially collected through a search or stream

    Four types of searches can be run:
    - Generic archive searches according to a particular query
    - Conversation searches based on an event, or a list of conversation IDs
    - User timeline searches based on an event, or a list of handles or user IDs
    - Quote searches of tweets that quote retweet event tweets

    Searches can be updated with tweets posted since the last time of collection
    or backfilled with tweets posted between a given time. This includes
    updating or backfilling individual conversation threads and user timelines.
    Quote searches cannot be updated or backfilled. Updating or backfilling
    conversations and timelines is slower than the initial search for them, so
    it is more efficient to try and only run the conversation and timeline
    searches once you are confident that you have all the other relevant event
    data, e.g. you have backfilled and updated the main event data already.
    Similarly, since quote searches cannot be updated or backfilled, it is most
    efficient to run it once the search/stream event tweets have been finalized

    All time parameters need to be RFC 3339 format, e.g. YYYY-MM-DDT00:00:00Z.
    There may be some inconsistencies in backfilling, updating, conversation,
    quote, and timeline searches relative to the main event tweets if you use a
    timezone other than UTC

    Parameters
    ----------
    event: str
        The name of the search event. This should be a unique name that can
        be used as an identifier for the set of tweets that result from this
        search. There must be a corresponding query configuration file with the
        same event name
    config_f: str
        The general configuration file to use
    max_results_per_page: int
        The maximum number of tweets to return per page of search. Defaults to
        the maximum 500. The minimum must be 10
    get_counts: bool
        Whether to count the number of tweets that will be returned by the
        queries, in place of actually searching the tweets. The time series
        count of tweets per granularity is output to a JSON file, each numbered
        according to the same ordr as the input query file
    granularity: str
        If counting, the granularity of the time series data, either `"minute"`,
        `"hour"`, or `"day"`. Defaults to `"hour"`
    get_convos: bool
        Whether to get the conversations for the event using the conversation
        IDs from the prior search or stream of the event, or for a list of input
        conversation IDs. It only collects conversations; it does not initiate a
        new event search to collect original event tweets. If True, `start_time`
        defaults to "`first_time`" and `end_time` defaults to "`last_time`"
    get_quotes: bool
        Whether to get tweets that quote those from an event search. Note, this
        is not needed for tweets that were collected from a stream: stream
        filter rules capture both tweets and those that quoted them, while
        search queries do not. If True, `start_time` defaults to "`first_time`"
        and `end_time` defaults to "`last_time`", unless otherwise set. Quote
        searches cannnot be updated or backfilled, so it is best to get quotes
        once the search tweets have been finalized, otherwise the only way to
        update/backfill the quotes is to perform another redundant full quote
        tweet search
    get_quotes_of_quotes: bool
        If a quote search has been run before (see `get_quotes`), whether to get
        quote tweets of those qoute tweets. This command can be run repeatedly,
        but becomes increasingly less efficiennt because _all_ quote twets, not
        just those from the prior run of `get_quotes_of_quotes`, will be
        searched
    get_timelines: bool
        Whether to get timelines for an event using the user IDs from a prior
        search or stream, or for a list of input user handles or IDs. If True,
        `start_time` defaults to `first_time` with `n_days_back=14` and
        `end_time` defaults to "`last_time`", unless otherwise set. Note,
        `n_days_back` will still be overriden to 14 if `start_time` is not
        manually as a parameter, even if a value is passed for `n_days_back`
    full_timelines: bool
        Whether to retrieve the full timelines of users. Defaults to False.
        If True, overrides `start_time` and `n_days_back`
    user_ids_f: str
        Filename of a newline delimited text file of user IDs or handles for
        collecting user timelines
    convo_ids_f: str
        Filename of a newline delimited text file of conversation IDs for
        collecting reply conversations
    update: bool
        Whether to update the dataset with tweets that have occurred since the
        last time the event search or stream was run. Defaults to updating to
        the present time starting from the last tweet time from event's streams
        or searches. If updating conversations or timelines, the `start_time`
        is set to latest tweet time available for each individual conversation
        or user, to avoid redundant searches. The parameters `end_time` and
        `n_days_after` can also be used together to specify until which time to
        run the update relative to the event. Cannot to be done at the same time
        as a backfill, and quote searches cannot be updated
    backfill: bool
        Whether to back fill the dataset with tweets that occurred before the
        stream or search was run. Defaults to backfilling from the beginning of
        the day of the first tweet time from the event's streams or searches to
        that first time. If updating conversations or timelines, the `end_time`
        is set to the earliest twweet time available for each individual
        conversation or user, to avoid redundant searches. The parameters
        `start_time` and `n_days_back` can also be used together to specify from
        which time to run the backfill relative to the event. Cannot be done at
        the same time as an update, and quote searches cannnot be backfilled
    start_time: str
        Sets the start time of the search. Overrides any start time set in the
        event configuration file. Use `"first_time"` to use the earliest tweet
        time recorded from a prior search or stream, and `"last_time"` to use
        the latest tweet time
    end_time: str
        Sets the end time of the search. Overrides any end time set in the event
        configuration file. Use `"last_time"` to use the latest tweet time
        recorded from a prior search or stream, and `"first_time"` to use the
        earliest tweet time. Use `"now"` to use the current date
    n_days_back: int
        How many days back to start the search relative to `start_time`. Note,
        it has to be `start_time` as passed as the parameter here, not in the
        event configuration file. Defaults to 0. Useful for backfills and
        collecting user timelines
    n_days_after: int
        How many days ahead to start the search relative to `end_time`. Note,
        it has to be `end_time` as passed as the parameter here, not in the
        event configuration file. Defaults to 0. Useful for updates
    append: bool
        Whether to append to the JSON file. If False, then overwrites any JSON
        file with the same name that already exists. Always appends if doing an
        update or a backfill. Always overwrites if doing counts
    write_count_files: bool
        Whether to write JSON time series count data when counting. Defaults to
        True if running a standard search. Defaults to False if running a
        timeline, conversation, or quote search (because they will produce many
        count files)
    verbose: bool
        Whether to print out information/updates of the search. Defaults to True
    update_interval: int
        How often to print updates of the number of tweets collected, in minutes
    """
    def __init__(self,
                 event,
                 config_f,
                 max_results_per_page=500,
                 get_counts=False,
                 granularity="hour",
                 get_convos=False,
                 get_quotes=False,
                 get_quotes_of_quotes=False,
                 get_timelines=False,
                 full_timelines=False,
                 user_ids_f=None,
                 convo_ids_f=None,
                 update=False,
                 backfill=False,
                 start_time=None,
                 end_time=None,
                 n_days_back=0,
                 n_days_after=0,
                 append=True,
                 write_count_files=None,
                 verbose=True,
                 update_interval=15):
        super().__init__(event=event,
                         query_type='search',
                         config_f=config_f,
                         append=append,
                         verbose=verbose,
                         update_interval=update_interval)
        self.update = update
        self.backfill = backfill
        self.get_counts = get_counts
        self.get_convos = get_convos
        self.get_quotes = get_quotes
        self.get_quotes_of_quotes = get_quotes_of_quotes
        self.get_timelines = get_timelines
        self.full_timelines = full_timelines
        self.start_time = start_time
        self.end_time = end_time
        self.n_days_back = n_days_back
        self.n_days_after = n_days_after

        self.unavail_user = False
        self.n_calls_last_15mins = 0
        self.rate_limit = self.config['rate_limits']['twitter']['search']
        if get_counts:
            self.search_endpoint = self.config['endpoints']['twitter']['count']
        else:
            self.search_endpoint = self.config['endpoints']['twitter']['search']

        if get_counts:
            self.query_number = 0
            self.query_tweet_count = 0
            self.total_query_tweet_count = 0

        # Set defaults if convo or timeline search
        if get_convos:
            self.query_type = 'convo_search'
            self.set_convo_defaults(convo_ids_f)
        elif get_quotes:
            self.query_type = 'quote_search'
            self.set_quote_defaults()
        elif get_timelines:
            self.query_type = 'timeline_search'
            self.set_timeline_defaults(user_ids_f)
        if convo_ids_f is None and user_ids_f is None:
            self.ids_input_f = None
        if not (get_convos or get_quotes or get_timelines):
            self.query_breadth = 'directly_from_search OR directly_from_stream'
            self.retweet_breadth = ''

        # Output JSON file
        if get_convos:
            self.out_json_fname = f"{self.out_json_dir}/{event}_conversations.json"
        elif get_timelines:
            self.out_json_fname = f"{self.out_json_dir}/{event}_timelines.json"
        if (append or update or backfill) and (not get_counts):
            self.write_mode = 'a+'
        else:
            self.write_mode = 'w+'
        # Whether to write counting files
        if write_count_files is None:
            if self.query_type == 'search':
                self.write_count_files = True
            else:
                self.write_count_files = False
        else:
            self.write_count_files = write_count_files
        # Open here and not general listening class in case final name changed
        # Count file gets opened in `update_query` since it dynamically changes
        if not get_counts:
            self.out_json_f = open(self.out_json_fname, self.write_mode)

        # Set up queries and query parameters
        self.get_earliest_latest_event_times()
        if get_timelines or get_convos or get_quotes:
            self.get_query_ids()

        self.set_start_time()
        self.set_end_time()

        if not (get_convos or get_timelines or get_quotes):
            self.set_search_queries()
        else:
            self.set_alt_search_queries()

        if self.verbose:
            print('Search params: ')
            print(f"\tStart time: {self.params['start_time']}")
            print(f"\tEnd time: {self.params['end_time']}\n")

        if get_counts:
            self.params['granularity'] = granularity
            self.n_zeros = len(str(self.queries.qsize()))
        else:
            self.params.update(self.request_fields)
            self.params['max_results'] = max_results_per_page

        self.update_query()


    def set_convo_defaults(self, convo_ids_f):
        """
        Sets default parameters if running a conversation search

        Parameters
        ----------
        convo_ids_f: str
            Filename of a newline-delimited file of conversation IDs, as passed
            to the class initiator
        """
        self.group_by_id = 'conversation_id'
        self.query_operator = 'conversation_id'
        self.query_breadth = 'directly_from_search OR directly_from_stream'
        self.retweet_breadth = ''
        if self.start_time is None:
            self.start_time = "first_time"
        if self.end_time is None:
            self.end_time = "last_time"
        if convo_ids_f is not None:
            self.ids_input_f = convo_ids_f


    def set_quote_defaults(self):
        """
        Sets default parameters if running a quote search
        """
        self.group_by_id = 'id,author_handle'
        self.query_operator = 'url'
        if not self.get_quotes_of_quotes:
            self.query_breadth = 'directly_from_search'
        else:
            self.query_breadth = 'directly_from_quote_search'
        self.retweet_breadth = 'AND retweeted IS NULL AND quote_count > 0'
        if self.start_time is None:
            self.start_time = "first_time"
        if self.end_time is None:
            self.end_time = "last_time"


    def set_timeline_defaults(self, user_ids_f):
        """
        Sets default parameters if running a timeline search

        Parameters
        ----------
        user_ids_f: str
            Filename of a newline-delimited file of user IDs or handles, as
            passed to the class initiator
        """
        self.group_by_id = 'author_id'
        self.query_operator = 'from'
        self.query_breadth = 'directly_from_search OR directly_from_stream'
        self.retweet_breadth = ''
        if self.start_time is None:
            self.start_time = "first_time"
            self.n_days_back = 14
        if self.end_time is None:
            self.end_time = "last_time"
        if user_ids_f is not None:
            self.ids_input_f = user_ids_f


    def get_earliest_latest_event_times(self):
        """
        If doing an update, backfill, conversation search OR a timeline or
        conversation search with an input file OR otherwise assuming that this
        event has been searched/streamed before, gets the earliest and latest
        times of tweets from the event
        """
        if (self.update or self.backfill or self.get_convos or self.get_quotes
            or ((self.get_timelines or self.get_convos) and self.ids_input_f is None)
            or self.start_time in {'first_time', 'last_time'}
            or self.end_time in {'first_time', 'last_time'}):

            tweet_table = self.tables['tweets']
            minmax_cmd = f"""
            SELECT
                MIN(created_at) as min_time,
                MAX(created_at) as max_time
            FROM
                {tweet_table}
            WHERE
                event = %(event)s
                AND ({self.query_breadth} {self.retweet_breadth})
            """
            self.cur.execute(minmax_cmd, {'event': self.event})
            self.first_time,self.last_time = self.cur.fetchone()


    def get_query_ids(self):
        """
        If doing a conversation or timeline search, either gets the conversation
        or user IDs from a prior search or stream of the event, or loads them
        from the input file
        """
        if self.ids_input_f is None:
            tweet_table = self.tables['tweets']
            breadth = f"{self.query_breadth} {self.retweet_breadth}"
            if self.get_convos or self.get_timelines:
                # tweets from directly_from_* will  extend the time boundary for
                # convos/user IDs, helping avoid duplicates if backfill/update had
                # to be stopped and restarted midway through
                # In this implementation, can't avoid duplicates for quotes because
                # the time bounds depend on what *quoted* tweets have been retrieved
                # while the search itself is still based on the original tweets
                breadth += f" OR directly_from_{self.query_type}"
            group_cmd = f"""
            SELECT
                {self.group_by_id},
                MIN(created_at) as min_time,
                MAX(created_at) as max_time
            FROM
                {tweet_table}
            WHERE
                event = %(event)s
                AND ({breadth})
            GROUP BY
                {self.group_by_id}
            """
            self.cur.execute(group_cmd, {'event': self.event})
            self.query_ids = self.cur.fetchall()
            if self.verbose:
                if self.get_convos:
                    print(f"{len(self.query_ids):,} conversations to retrieve")
                elif self.get_quotes:
                    print(f"{len(self.query_ids):,} tweets to get quotes for")
                else:
                    print(f"{len(self.query_ids):,} timelines to retrieve")
        else:
            self.query_ids = []
            with open(self.ids_input_f, 'r') as f_in:
                for line in f_in:
                    self.query_ids.append((line.strip(), None, None))
            if self.verbose:
                if self.get_timelines:
                    print(f"{len(self.query_ids):,} timelines to retrieve")
                elif self.get_convos:
                    print(f"{len(self.query_ids):,} conversations to retrieve")


    def set_start_time(self):
        """
        Sets the start time to use for the search based on the user input
        """
        if self.full_timelines:
            self.params['start_time'] = None
        elif self.start_time is not None:
            if self.start_time == 'first_time':
                start_datetime = self.first_time
            elif self.start_time == 'last_time':
                start_datetime = self.last_time
            else:
                start_datetime = dateparser.parse(self.start_time)
            start_datetime = start_datetime - timedelta(self.n_days_back)
            self.params['start_time'] = start_datetime.strftime(date_format)
        elif self.backfill:
            start_datetime = datetime(self.first_time.year, self.first_time.month,
                                      self.first_time.day)
            self.params['start_time'] = start_datetime.strftime(date_format)
        elif self.update:
            self.params['start_time'] = self.last_time.strftime(date_format)
        else:
            self.params['start_time'] = None


    def set_end_time(self):
        """
        Sets the end time to use for the search based on the user input
        """
        if self.full_timelines:
            self.params['end_time'] = None
        elif self.end_time is not None:
            if self.end_time == 'last_time':
                end_datetime = self.last_time
            elif self.end_time == 'first_time':
                end_datetime = self.first_time
            elif self.end_time == 'now':
                end_datetime = datetime.now()
            else:
                end_datetime = dateparser.parse(self.end_time)
            end_datetime = end_datetime + timedelta(self.n_days_after)
            self.params['end_time'] = end_datetime.strftime(date_format)
        elif self.backfill:
            self.params['end_time'] = self.first_time.strftime(date_format)
        elif self.update:
            self.params['end_time'] = datetime.now().strftime(date_format)
        else:
            self.params['end_time'] = None


    def set_search_queries(self):
        """
        If doing a generic search (not conversations or timelines), reads the
        queries from the event file, and does final processing of the start
        and end time of the queries
        """
        self.queries = Queue()
        self.query_f = f"{self.config['input']['twitter']['search']}/{self.event}.yaml"
        with open(self.query_f) as fin:
            search_queries = yaml.load(fin, Loader=yaml.Loader)

        # Set start and end time if not already set
        if 'start_time' in search_queries and self.params['start_time'] is None:
            start_datetime = dateparser.parse(search_queries['start_time'])
            start_datetime -= timedelta(self.n_days_back)
            self.params['start_time'] = start_datetime.strftime(date_format)
        elif self.params['start_time'] is None:
            warnings.warn("WARNING: start_time not set for generic search")
        if 'end_time' in search_queries and self.params['end_time'] is None:
            end_datetime = dateparser.parse(search_queries['end_time'])
            end_datetime += timedelta(self.n_days_after)
            self.params['end_time'] = end_datetime.strftime(date_format)

        # Add queries
        for q in search_queries['queries']:
            self.queries.put((q, self.params['start_time'], self.params['end_time']))


    def set_alt_search_queries(self):
        """
        If doing a conversation, quote, or timeline search, formats the IDs into
        queries to the send to the API
        """
        cur_query = []
        cur_query_len = 0
        self.queries = Queue()
        for query_info in self.query_ids:
            if not self.get_quotes:
                q_id,min_time,max_time = query_info
                query = f"{self.query_operator}:{q_id}"
            else:
                q_id,q_handle,min_time,max_time = query_info
                query = f'url:"https://twitter.com/{q_handle}/status/{q_id}"'
            query_len = len(query)
            if self.backfill:
                q_start_time = self.params['start_time']
                q_end_time = min_time.strftime(date_format)
                self.queries.put((query, q_start_time, q_end_time))
            elif self.update:
                q_start_time = max_time.strftime(date_format)
                q_end_time = self.params['end_time']
                self.queries.put((query, q_start_time, q_end_time))

            # len of all queries + " OR " + new query + " OR " for new query
            elif cur_query_len + 4*(len(cur_query) - 1) + query_len + 4 > 1024:
                self.queries.put((' OR '.join(cur_query),
                                  self.params['start_time'],
                                  self.params['end_time']))
                cur_query = [query]
                cur_query_len = query_len
            else:
                cur_query.append(query)
                cur_query_len += query_len

        # Put final query
        if not (self.update or self.backfill):
            self.queries.put((' OR '.join(cur_query), self.params['start_time'],
                              self.params['end_time']))


    def update_query(self):
        """
        Updates the current query, tells search to stop if no more queries
        """
        if self.get_counts:
            if self.query_type == 'search' and self.total_query_tweet_count > 0 and self.verbose:
                print(f'\nNumber of tweets in query: {self.query_tweet_count:,}')
            self.query_tweet_count = 0
            # Update filename of JSON
            if self.query_number > 0 and self.write_count_files:
                self.out_json_f.close()
            self.query_number += 1
            pad_num = str(self.query_number).zfill(self.n_zeros)
            self.out_json_fname = f"{self.out_json_dir}/{self.event}_counts_{pad_num}.json"
        if self.queries.qsize() > 0:
            q,q_start,q_end = self.queries.get(block=False)
            self.params['query'] = q
            self.params['start_time'] = q_start
            self.params['end_time'] = q_end
            if 'next_token' in self.params:
                del self.params['next_token']
            if self.query_type == 'search' and self.verbose:
                print('\n\tUpdated query')
                print(f"\t{self.params['query']}")
            # Put this in this condition so we don't make an extra count file
            if self.get_counts and self.write_count_files:
                self.out_json_f = open(self.out_json_fname, self.write_mode)
        else:
            self.stop = True
            if self.verbose:
                print('\nNo more queries to run')


    def search(self):
        """
        Connects to the Twitter full search archive and writes out the returned
        data
        """
        signal.signal(signal.SIGINT, self.exit_handler)

        # Get tweets from search
        while not self.stop:
            self.check_rate_limit()

            response = requests.get(self.search_endpoint, headers=self.headers,
                                    params=self.params)
            self.n_calls_last_15mins += 1
            self.check_response_exception(response)
            if self.pause or self.temp_unavail:
                continue

            # Parse tweets
            response_json = response.json()
            self.manage_writing(response_json)
            if self.stop:
                return

            if 'next_token' in response_json['meta']:
                self.params['next_token'] = response_json['meta']['next_token']
            else:
                self.update_query()

            self.limit_rate()


    def count(self):
        """
        Connects to the counting endpoint to see how many tweets a given set of
        queries will return
        """
        signal.signal(signal.SIGINT, self.exit_handler)

        # Count tweets from search
        while not self.stop:
            self.check_rate_limit()

            response = requests.get(self.search_endpoint, headers=self.headers,
                                    params=self.params)
            self.n_calls_last_15mins += 1
            self.check_response_exception(response)
            if self.pause or self.temp_unavail:
                continue

            # Parse counts
            response_json = response.json()
            self.manage_counting(response_json)

            if self.stop:
                return

            if 'next_token' in response_json['meta']:
                self.params['next_token'] = response_json['meta']['next_token']
            else:
                self.update_query()

            self.limit_rate()


    def manage_counting(self, response_json):
        """
        Coordinates the writing of data, namely handling exceptions and updating
        the count of data returned from the API

        Parameters
        ----------
        response_json: dict
            JSON from an API response produced via the response library
        """
        try:
            # Get total number of tweets
            total_count = response_json['meta']['total_tweet_count']
            self.query_tweet_count += total_count
            self.total_query_tweet_count += total_count

            # Write out counts for granularity
            if self.write_count_files:
                counts = response_json['data']
                for count in counts:
                    out_str = json.dumps(count)
                    self.out_json_f.write(f"{out_str}\n")
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


# ------------------------------------------------------------------------------
# --------------------------- End of class definition --------------------------
# ------------------------------------------------------------------------------
def main(event, config_f, max_results_per_page, get_counts, granularity,
         get_convos, get_quotes, get_quotes_of_quotes, get_timelines,
         full_timelines, user_ids_f, convo_ids_f, update, backfill, start_time,
         end_time, n_days_back, n_days_after, append, write_count_files,
         verbose, update_interval):
    """
    Connects to the Twitter API v2 search endpoint

    See above class definition for parameter explanations
    """
    # Connect to search endpoint
    search =SearchListener(event=event,
                           config_f=config_f,
                           max_results_per_page=max_results_per_page,
                           get_counts=get_counts,
                           granularity=granularity,
                           get_convos=get_convos,
                           get_quotes=get_quotes,
                           get_quotes_of_quotes=get_quotes_of_quotes,
                           get_timelines=get_timelines,
                           full_timelines=full_timelines,
                           user_ids_f=user_ids_f,
                           convo_ids_f=convo_ids_f,
                           update=update,
                           backfill=backfill,
                           start_time=start_time,
                           end_time=end_time,
                           n_days_back=n_days_back,
                           n_days_after=n_days_after,
                           append=append,
                           write_count_files=write_count_files,
                           verbose=verbose,
                           update_interval=update_interval)
    if get_counts:
        search.count()
    else:
        search.search()

    search.conn.commit()
    search.cur.close()
    search.conn.close()
    # Last file gets closed during counting
    if not get_counts:
        search.out_json_f.close()

    if verbose and not get_counts:
        print('Closed writing and committed changes to database')
        now = datetime.now().strftime("%Y-%m-%d %I:%m%p")
        print(f"\nSearch finished at {now}")
        print(f"\n{search.n_tweets_total:,} tweets returned by API\n")
    elif verbose and get_counts:
        now = datetime.now().strftime("%Y-%m-%d %I:%m%p")
        print(f"\nCounting finished at {now}")
        print(f"Estimated {search.total_query_tweet_count:,} tweets across all queries\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Twitter archive search")
    parser.add_argument("event", type=str)
    parser.add_argument("-config", type=str, default="config.yaml")
    parser.add_argument("-max_results_per_page", type=int, default=500)
    parser.add_argument("-user_ids_f", type=str, default=None)
    parser.add_argument("-convo_ids_f", type=str, default=None)
    parser.add_argument("-start_time", type=str, default=None)
    parser.add_argument("-end_time", type=str, default=None)
    parser.add_argument("-n_days_back", type=int, default=0)
    parser.add_argument("-n_days_after", type=int, default=0)
    parser.add_argument("-update_interval", type=int, default=15)
    parser.add_argument("-granularity", type=str, default="hour")
    # Booleans can't be parsed directly, so you set a flag for each option
    parser.add_argument("--get_counts", dest="get_counts", action="store_true")
    parser.add_argument("--get_convos", dest="get_convos", action="store_true")
    parser.add_argument("--get_quotes", dest="get_quotes", action="store_true")
    parser.add_argument("--get_quotes_of_quotes", dest="get_quotes_of_quotes", action="store_true")
    parser.add_argument("--get_timelines", dest="get_timelines", action="store_true")
    parser.add_argument("--full_timelines", dest="full_timelines", action="store_true")
    parser.add_argument("--update", dest="update", action="store_true")
    parser.add_argument("--backfill", dest="backfill", action="store_true")
    parser.add_argument("--append", dest="append", action="store_true")
    parser.add_argument("--verbose", dest="verbose", action="store_true")
    parser.add_argument("--quiet", dest="verbose", action="store_false")
    parser.add_argument("--overwrite", dest="append", action="store_false")
    parser.add_argument("--write_count_files", dest="write_count_files", action="store_true")
    parser.add_argument("--no_count_files", dest="write_count_files", action="store_false")
    parser.set_defaults(get_counts=False, get_convos=False, get_quotes=False,
                        get_timelines=False, get_quotes_of_quotes=False,
                        append=True, verbose=True, full_timelines=False,
                        update=False, backfill=False, write_count_files=None)

    args = parser.parse_args()

    main(args.event,
         args.config,
         args.max_results_per_page,
         args.get_counts,
         args.granularity,
         args.get_convos,
         args.get_quotes,
         args.get_quotes_of_quotes,
         args.get_timelines,
         args.full_timelines,
         args.user_ids_f,
         args.convo_ids_f,
         args.update,
         args.backfill,
         args.start_time,
         args.end_time,
         args.n_days_back,
         args.n_days_after,
         args.append,
         args.write_count_files,
         args.verbose,
         args.update_interval)
