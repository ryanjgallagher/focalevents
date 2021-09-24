Data Across Queries
===================

The :code:`focalevents` tools are designed with multiple related queries in mind, whether they be from a stream, search, or auxiliary search for conversations, quotes, or timelines. There are five boolean fields in the :code:`tweets` table to distinguish the query source of any given tweet:

- :code:`from_stream`,
- :code:`from_search`,
- :code:`from_quote_search`,
- :code:`from_convo_search`,
- :code:`from_timeline_search`,

All tweets that were returned by a particular query will be marked as :code:`True` in the corresponding :code:`from_*` field. Multiple columns can be :code:`True` if a tweet was returned by more than one type of query. This allows you to distinguish the query source of different tweets, while still organizing them together through their :code:`event` names.


Referenced Tweets
-----------------

The :code:`tweets` table distinguishes between tweets that are returned directly in response to a query from the API, and `referenced tweets <https://developer.twitter.com/en/docs/twitter-api/data-dictionary/object-model/tweet/>`_ that are returned because they were retweeted, quoted, or replied to. There are five additional boolean fields corresponding to the ones above that indicate whether a tweet was referenced or not:

- :code:`directly_from_stream`
- :code:`directly_from_search`
- :code:`directly_from_quote_search`
- :code:`directly_from_convo_search`
- :code:`directly_from_timeline_search`

*All* tweets that were returned by a particular query, referenced or not, will be marked as :code:`True` in the :code:`from_*` field. Any tweet that was returned *directly* by a query (i.e. it is not just a referenced tweet) will be marked as :code:`True` in the :code:`directly_from_*` field. Tweets that are only referenced tweets then can be identified by looking for rows where :code:`from_* AND NOT directly_from_*`.


Quote Tweet Matching in Streams and Searches
--------------------------------------------

The filter stream matches on tweets that match a certain rule *and* quote tweets where the `quoted tweet matches the rule <https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query#quote-tweets>`_. This means that if we did not previously see a quoted tweet in a stream (i.e. if we started our stream after the quoted tweet was posted), then that tweet will be marked as :code:`False` in the :code:`directly_from_stream` field, even though it may be the tweet with the keyword match. For this reason, it is recommended to backfill the stream tweets with a search query after the stream is done, so that quoted tweets that were matched by the stream will be marked as :code:`True` in the :code:`directly_from_search` field. This allows us to identify all directly relevant tweets by looking for those that are :code:`directly_from_stream AND directly_from_search`.
