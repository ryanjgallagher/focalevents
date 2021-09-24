Twitter Cookbook
================

Data is collected from Twitter using their v2 API endpoints and syntax. This codebase assumes that you have academic access with your tokens because they are needed to utilize the API's full-archive search capabilities.

The following data can be collected around a focal event on Twitter:

- Tweets from the filter stream
- Tweets from the full-archive search
- Conversation reply threads for tweets collected from a focal event
- Quote tweets quoting any tweets collected from a focal event
- Full user timelines of users who tweeted during a focal event

After setting up the query file, performing a full archive search is as simple as:

.. code-block:: bash

    python -m twitter.search event_name

Similarly, connecting to the filter stream is as simple as:

.. code-block:: bash

    python -m twitter.stream event_name


.. toctree::
    :maxdepth: 1

    stream
    search
    updates_and_backfills
    auxiliary_searches
    data
    organization
