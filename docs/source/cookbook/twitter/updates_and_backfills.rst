.. _updates_and_backfills:

Updates and Backfills
=====================

Once a search or stream has been run around a focal event, it is easy to update or backfill the tweets with additional data.

Updates and End Times
---------------------

The focal event can be updated with all the tweets that have occurred since the stream/search was run. To do this, use the :code:`update` flag

.. code-block:: bash

    python -m twitter.search event_name --update

By default, the update looks at the last focal event tweet that came from the stream/search and gets all tweets that occurred from then to the moment of running the update.

To change when the update ends, we can use the :code:`end_time` parameter. A specific time can be passed to the :code:`end_time`, and the update will run from the last search/stream tweet to that time. For example, if we want to run our update until 11am UTC on August 18th, 2021, then we can enter

.. code-block:: bash

    python -m twitter.search event_name --update -end_time 2021-08-18T11:00:00.00Z

We can also set the :code:`end_time` to the value :code:`last_time` and use the parameter :code:`n_days_after` to modify how many days after the last search/stream tweet time that we want to run the update. For example, if we wanted to run the update for the 3 days following the last tweet from our search/stream, then we would do

.. code-block:: bash

    python -m twitter.search event_name --update -end_time last_time -n_days_after 3


Backfills and Start Times
-------------------------

In addition to updating our dataset, we can also backfill it with tweets that occurred before the earliest tweet in our search/stream. By default, the backfill runs from the beginning of the day of the earliest tweet from the search/stream until the time of that tweet. We can run that basic backfill as

.. code-block:: bash

    python -m twitter.search event_name --backfill

Like the update, we can also set the backfill start manually using the :code:`start_time`. The :code:`start_time` can either be a specific time or a time relative to the :code:`first_time` using the :code:`n_days_before` parameter. For example, if we wanted to get all the focal event tweets that occurred in the week prior to the first tweet in our search/stream, then we would enter

.. code-block:: bash

    python -m twitter.search event_name --backfill -start_time first_time -n_days_before 7

.. note::

    All time parameters need to be RFC 3339 format:

    YYYY-MM-DDT00:00:00.00Z

.. note::

    The start and end times can be used together for any search, not just updates and backfills. That is, a different :code:`start_time` can be used for an update, a different :code:`end_time` can be used for a backfill, and in general both parameters can be used to produce any time window.
