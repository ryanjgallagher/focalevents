.. _queries:

Creating a Query
================

Queries are specified in files separate from the code that runs them. This modularity avoids hard coding the queries into the code itself and risking them being accidentally overwritten or modified between searches. Placing queries in their own files also makes them easier to share them, promoting transparency and replicability.

Event Names
-----------

All data is organized around an *event name*. This name should be a unique signifier for the focal event around which you want to collect data.

The event name is specified through the name of the query file. For example, say we want to search for tweets about Facebook's Oversight Board. Then we can name our event "facebook_oversight" and create a corresponding search query file :code:`facebook_oversight.yaml`. The query file should be placed in the appropriate :code:`input` directory. For example, if we are running a Twitter search, then we will place our query file in the directory :code:`input/twitter/search`.


Query Structure
---------------

The structure and syntax of the query file depends on the platform being queried and the endpoint's query operators.

Twitter Search
^^^^^^^^^^^^^^

Twitter search query files are YAML files with three fields: :code:`queries`, :code:`start_time`, and :code:`end_time`. The :code:`queries` field allows you to list multiple queries sequentially, each of which will be sent to the Twitter API. The start and end times follow the RFC 3339 format, e.g. YYYY-MM-DDT00:00:00Z

See `here <https://github.com/ryanjgallagher/focalevents/blob/main/input/twitter/search/facebook_oversight.yaml/>`_ for an example of a Twitter search query file. See `Twitter's documentation <https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query/>`_ for details on how to build a Twitter search query.

Twitter Filter Stream
^^^^^^^^^^^^^^^^^^^^^

Twitter filter stream query files are YAML files with one field: :code:`rules`. The :code:`rules` field allows you to list multiple filter rules sequentially, each of which will be sent to the Twitter API. Each rule should have two fields itself: :code:`value` and :code:`tag`. The :code:`value` is the filter rule itself. The :code:`tag` is a colloquial description of the filter rule.

See `here <https://github.com/ryanjgallagher/focalevents/blob/main/input/twitter/stream/facebook_oversight.yaml/>`_ for an example of a Twitter filter stream query file. See `Twitter's documentation <https://developer.twitter.com/en/docs/twitter-api/tweets/filtered-stream/integrate/build-a-rule/>`_ for details on how to build a filter rule for Twitter's stream.
