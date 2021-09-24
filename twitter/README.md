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

## Documentation

See the [full documentation]() for more information about searching and streaming tweets, and how to collect conversations, quotes, and timelines.
