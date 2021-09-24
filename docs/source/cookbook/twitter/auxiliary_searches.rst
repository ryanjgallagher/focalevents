.. _auxiliary:

Getting Conversations, Quotes, and Timelines
============================================

Reply threads of tweets from a focal event, quote tweets that quote focal event tweets, and timelines of users from a focal event can also be collected through searches. They are run using the :code:`get_convos`, :code:`get_quotes`, and :code:`get_timelines` flags, respectively.

For example, if we want to get all of the reply threads of our focal tweets then we can run:

.. code-block:: bash

    python -m twitter.search event_name --get_convos

*Conversation* and *quote* searches default to collecting tweets that occurred between the first and last search/stream tweets. In other words, :code:`start_time` defaults to :code:`first_time` and :code:`end_time` defaults to :code:`last_time`.

If we want to alter those defaults and get all of the replies that occurred during the focal event and 2 days after the focal event, for example, then we can use the :code:`end_time` parameter to change when the search ends:

.. code-block:: bash

    python -m twitter.search event_name --get_convos -end_time last_time -n_days_after 2

*Timeline* searches default to collecting user timelines from 14 days *before* the focal event to the time of the last tweet of the focal event. In other words, :code:`start_time` defaults to :code:`first_time` with :code:`n_days_back` as 14, and :code:`end_time` defaults to :code:`last_time`. The parameters :code:`start_time`, :code:`n_days_back`, :code:`end_time`, and :code:`n_days_after` can be used in any combination to set other timeline search ranges. There is also a flag :code:`full_timelines` to collect all of the focal event users' tweets.

For example, if we want to get user timelines from 30 days before the focal event to 7 days after, we can run the following:

.. code-block:: bash

    python -m twitter.search event_name --get_timelines -start_time first_time -n_days_back 30 -end_time last_time -n_days_after 7

*Conversation* and *timeline* searches can also be run as updates or backfills. For example, you can update a conversation search that was already run, or backfill user timelines to an earlier date.

.. note::

    It is recommended that you finish all updating and backfilling of the core stream/search focal event tweets *before* running conversation, quote, and timeline searches. This is because updating/backfilling conversation and timeline searches is much slower than initially collecting them. *Quote* searches cannot currently be updated or backfilled without performing redundant queries to the API, so they should only be run once the search/stream tweets are finished being updated/backfilled.

.. note::

    if :code:`full_timelines` is specified, the user timelines that are returned by the API are truly full timelines because we use the full-archive search endpoint. This is unlike Twitter's v1 and v2 API user timeline endpoints, which only return the most recent 3,200 tweets from any user.


Inputting Conversation and User IDs
-----------------------------------

Sometimes we may want reply threads or user timelines based on a set of input IDs, rather than from a prior search/stream.

You can provide a filename to either :code:`user_ids_f` or :code:`convo_ids_f` and run a timeline or conversation search as a standalone search. *The query still needs to be given an event name at the command line.* The files should be new-line delimited, where there is one ID per line.

For example, if we had a file of user IDs and we wanted to get their full timelines, then we can retrieve them as

.. code-block:: bash

    python -m twitter.search event_name -user_ids_f path/to/user_ids.txt --full_timelines

Because these are standalone searches, the :code:`start_time` and :code:`end_time` have to be set manually at the command line as specific times and dates. If getting full user timelines, then only :code:`full_timelines` needs to be passed.
