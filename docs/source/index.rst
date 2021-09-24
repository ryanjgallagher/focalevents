Social Media Focal Events Listener
==================================

The :code:`focalevents` codebase provides tools for organizing data collected around focal events on social media.

It is often difficult to organize data from multiple API queries. For example, we may collect tweets when a hashtag starts trending by using Twitter's filter stream. Later, we may make a separate query to the search endpoint to backfill our stream with what we missed before we started it, or update it with tweets that occurred since we stopped it. We may also want to get reply threads, quote tweets, or user timelines based on the tweets we collected. All of these queries are related to a common focal event—the hashtag—but they require several separate calls to the API. It is easy for these multiple queries to result in many disjoint files, making it difficult to organize, merge, update, backfill, and preprocess them quickly and reliably.

To address these issues, :code:`focalevents` can be used to organize social media focal event data collected from Twitter's v2 API using academic credentials and PostgreSQL. It is easy to do any of the following with the tools here:

- Query Twitter's full archive or filter stream for focal event data
- Backfill and update those queries with additional data
- Collect conversation threads and quote tweets of focal event tweets
- Retrieve full user timelines for any user tweeting during a focal event


All of these functionalities are easy, single line commands, rather than long multi-line scripts, as are typically needed to read IDs, query the API, output data, and merge it with existing data. This allows researchers to design more complex studies of social media data, and spend more time focusing on data analysis, rather than data storage and maintenance.


.. toctree::
    :maxdepth: 3

    installation
    cookbook/index
