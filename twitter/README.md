# Twitter Focal Events

Data is collected from Twitter using their v2 API endpoints and syntax. This codebase assumes that you have academic access with your tokens because they are needed to utilize the API's full-archive search capabilities.

The following data can be collected around a focal event on Twitter:

- Tweets from the filter stream
- Tweets from the full-archive search
- Conversation reply threads from tweets collected from a focal event stream/search
- Quote tweets quoting any tweets collected from a focal event search ([not needed for stream tweets](https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query#quote-tweets))
-  User timelines of users who tweeted during a focal event stream/search

In addition, there are tools for easily updating and backfilling any of the above queries (except quote tweets). All of the data is linked through the `event` field in the PostgreSQL tables (see below for details on table organization).


## Collecting Data from Streams

First, rules need to be specified in the [event query configuration file](https://github.com/ryanjgallagher/focalevents) according to Twitter's filter stream [syntax rules](https://developer.twitter.com/en/docs/twitter-api/tweets/filtered-stream/integrate/build-a-rule). See an example [here](https://github.com/ryanjgallagher/focalevents/blob/main/input/twitter/stream/facebook_oversight.yaml).

Once the event configuration file is ready, the command for streaming tweets is

```
python -m twitter.stream event_name
```

The stream can be cancelled at any time with `CTRL+C`.


## Collecting Data from Searches

All other Twitter data is collected as a type of search. Like the stream, the search needs to be specified using an [event configuration file](https://github.com/ryanjgallagher/focalevents) using Twitter's [search syntax](https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query). See an example [here](https://github.com/ryanjgallagher/focalevents/blob/main/input/twitter/search/facebook_oversight.yaml), and note that the search configuration format is different than the stream configuration format.

Once the event configuration file is ready, the command for streaming tweets is

```
python -m twitter.search event_name
```

The search can be cancelled at any time with `CTRL+C`.


### Counting

It can be helpful to know how many tweets will be returned from a search before running it so that you can be prepared to store them and not exceed the monthly tweet quota. To estimate the number of tweets that will be returned without actually running the search, use the `get_counts` flag:

```
python -m twitter.search event_name --get_counts
```

This accesses Twitter's [count endpoint](https://developer.twitter.com/en/docs/twitter-api/tweets/counts/api-reference/get-tweets-counts-all) and returns time series count data in JSON files in the `output` directory. If you have more than one query, then there will be one file per query, numbered in the same order that they appear in the input query file. For a standard search, these files are written out by default. If you do not want them written out, and only want the console to print the number of estimated tweets, then you can use the `no_count_files` flag. For timeline, conversation, and quote searches (see below for more details), count files are not written out by default because they can potentially produce many files that are not well ordered (unless using an input ID file). If you would still like to return the files, use the `write_count_files` flag.

You can set the granularity of the time series count data to be `minute`, `hour`, or `day`:

```
python -m twitter.search event_name --get_counts -granularity hour
```


### Updates and Backfills

Once a search or stream has been run around a focal event, it is easy to update or backfill the tweets with additional data.

The focal event can be updated with all the tweets that have occurred since the stream/search was run. To do this, use the `update` flag

```
python -m twitter.search event_name --update
```

By default, the update looks at the last focal event tweet that came from the prior stream/search and gets all tweets that occurred from then to the moment of running the update. To change when the update ends, we can use the `end_time` parameter. A specific time can be passed to the `end_time`, and the update will run from the last search/stream tweet to that time. For example, if we want to run our update until 11am UTC on August 18th, 2021, then we would enter

```
python -m twitter.search event_name --update -end_time 2021-08-18T11:00:00.00Z
```

Note, all time parameters need to be RFC 3339 format, e.g. YYYY-MM-DDT00:00:00.00Z. We can also set the `end_time` to the value `last_time` and use the parameter `n_days_after` to modify how many days after the last search/stream tweet time that we want to run the update. For example, if we wanted to run the update for the 3 days following the last tweet from our search/stream, then we would do

```
python -m twitter.search event_name --update -end_time last_time -n_days_after 3
```

In addition to updating our dataset, we can also backfill it with tweets that occurred before we ran our search and/or stream. By default the backfill runs from the beginning of the day of the earliest tweet from the prior search/stream until the time of that tweet. We can run that basic backfill as

```
python -m twitter.search event_name --backfill
```

Like the update, we can also set the backfill start manually using the `start_time`. The `start_time` can either be a specific time or a time relative to the `first_time` using the `n_days_before` parameter. For example, if we wanted to get all the focal event tweets that occurred in the week prior to the first tweet in our search/stream, then we would enter

```
python -m twitter.search event_name --backfill -start_time first_time -n_days_before 7
```


### Conversation, Quote, and Timeline Searches

Reply threads of tweets from a focal event, quote tweets that quote focal event tweets, and timelines of users from a focal event can also be collected through searches. They are run using the `get_convos`, `get_quotes`, and `get_timelines` flags. For example, if we want to get all of the reply threads of our focal tweets then we would run

```
python -m twitter.search event_name --get_convos
```

The **conversation search** and **quote search** default to collecting reply threads and quotes that occurred between the first and last search/stream tweets. In other words, `start_time` defaults to `first_time` and `end_time` defaults to `last_time`. If we wanted to get, for example, all of the replies that occurred during the focal event and 2 days after the focal event, then we can use the `end_time` parameter to change when the search ends:

```
python -m twitter.search event_name --get_convos -end_time last_time -n_days_after 2
```

The **timeline search** defaults to collecting user timelines from 14 days _before_ the focal event to the time of the last tweet of the focal event, i.e. `start_time` defaults to `first_time` with `n_days_back` as 14, and `end_time` defaults to `last_time`. The parameters `start_time`, `n_days_back`, `end_time`, and `n_days_after` can be used in any combination to set other timeline search ranges. There is also a flag `full_timelines` if you want to collect all of the focal event users' tweets. Note, because user timelines are collected using the full-archive search, these are _full_ user timelines, not just the most recent 3,200 user tweets, as was the case when using the user timeline endpoint for v1 and v2 of Twitter's API.

```
python -m twitter.search event_name --get_timelines --full_timelines
```

**Conversation searches** and **timeline searches** can also be run as updates or backfills. So, for example, you can update conversation searches that were already run, or backfill user timelines to an even earlier date. It is recommended that you finish all updating and backfilling of the core stream/search focal event tweets _before_ running conversation, quote, and timeline searches. This is because updating/backfilling conversation and timeline searches is much slower than initially collecting them. **Quote searches** cannot currently be updated or backfilled without performing redundant queries to the API, so they should only be run once the search/stream tweets are finished being updated/backfilled.


### Inputting conversation and user IDs

Sometimes we may want reply threads or user timelines based on a set of input IDs, rather than from a prior search or query. For convenience, you can provide a filename to either `user_ids_f` or `convo_ids_f` to run a timeline or conversation search as a standalone search. The query still needs to be given an event name at the command line. The files should be new line delimited, where there is one ID per line.

For example, if we had a file of user IDs and we wanted to get their full timelines, then we can retrieve them as

```
python -m twitter.search event_name -user_ids_f path/to/user_ids.txt --full_timelines
```

Because these are standalone searches, the `start_time` and `end_time` have to be set manually at the command line as specific times and dates. If getting full user timelines, then only `full_timelines` needs to be passed.


## Data Organization

### Tables and Fields

Regardless of the query, data from tweets, users, media, and places are stored in the PostgreSQL database. They are available under the `twitter` schema in the tables `tweets`, `users`, `media`, and `places`. Each row is uniquely identified by the `id` of the object and the `event` name of the focal event.

The following additional [fields](https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/tweet) are stored for tweets (along with the `from_*` and `directly_from_*` fields described below).
- `text`
- `lang`
- `author_id`
- `author_handle`
- `created_at`
- `conversation_id`
- `possibly_sensitive`
- `reply_settings`
- `source`
- `author_follower_count`
- `retweet_count`
- `reply_count`
- `like_count`
- `quote_count`
- `replied_to`
- `replied_to_author_id`
- `replied_to_handle`
- `replied_to_follower_count`
- `quoted`
- `quoted_author_id`
- `quoted_handle`
- `quoted_follower_count`
- `retweeted`
- `retweeted_author_id`
- `retweeted_handle`
- `retweeted_follower_count`
- `mentioned_author_ids`
- `mentioned_handles`
- `hashtags`
- `urls`
- `media_keys`
- `place_id`

The following [fields](https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/user) are stored for users.
- `name`
- `username`
- `created_at`
- `description`
- `location`
- `pinned_tweet_id`
- `followers_count`
- `following_count`
- `tweet_count`
- `url`
- `profile_image_url`
- `description_urls`
- `description_hashtags`
- `description_mentions`
- `verified`

The following [fields](https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/media) are stored for media.
- `type`
- `duration_ms`
- `height`
- `width`
- `preview_image_url`
- `view_count`

The following [fields](https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/place) are stored for places. Place objects returned by the API are assumed to be static and so they are not indexed by `event` (i.e. there is no `event` field).
- `name`
- `full_name`
- `country`
- `country_code`
- `geo`
- `place_type`

### Referenced Tweets

The `tweets` table distinguishes between tweets that are returned directly in response to a query from the API, and [referenced tweets](https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/tweet) that are returned because they were referenced, quoted, or replied to the query tweets. There are five different types of boolean fields that indicate what search a tweet was from and whether it is a refernced tweeet or not:

- `from_stream`, `directly_from_stream`
- `from_search`, `directly_from_search`
- `from_quote_search`, `directly_from_quote_search`
- `from_convo_search`, `directly_from_convo_search`
- `from_timeline_search`, `directly_from_timeline_search`

_All_ tweets that were returned by a particular query, referenced or not, will be marked as `True` in the `from_*` field (where `*` is any of the query types above). Any tweet that was returned _directly_ by a query (i.e. it is not just a referenced tweet) will be marked as `True` in the `directly_from_*` field. Tweets that are only referenced tweets then can be identified by looking for rows where `from_* AND NOT directly_from_*`.

**Note:** The filter stream matches on tweets that match a certain rule _and_ quote tweets where the [_quoted_ tweet matches the rule](https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query#quote-tweets). _If we did not previously see the quoted tweet in the stream_ (i.e. if we started our stream after that tweet was posted), then that tweet will be marked as `False` in the `directly_from_stream` field, even though it may be the tweet with the keyword match. For this reason, it is recommended to backfill the stream tweets with a search query after the stream is done, so that quoted tweets that were matched by the stream will be marked as `True` in the `directly_from_search` field. This allows us to identify all directly relevant tweets by looking for those that are `directly_from_stream AND directly_from_search`.
