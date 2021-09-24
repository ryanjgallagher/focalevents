# Social Media Focal Events

The `focalevents` codebase provides tools for organizing data collected around focal events on social media.

It is often difficult to organize data from multiple API queries. For example, we may collect tweets when a hashtag starts trending by using Twitter’s filter stream. Later, we may make a separate query to the search endpoint to backfill our stream with what we missed before we started it, or update it with tweets that occurred since we stopped it. We may also want to get reply threads, quote tweets, or user timelines based on the tweets we collected. All of these queries are related to a common focal event—the hashtag—but they require several separate calls to the API. It is easy for these multiple queries to result in many disjoint files, making it difficult to organize, merge, update, backfill, and preprocess them quickly and reliably.

To address these issues, `focalevents` can be used to organize social media focal event data collected from Twitter’s v2 API using academic credentials and PostgreSQL. It is easy to do any of the following with the tools here:

- Query Twitter’s full archive or filter stream for focal event data
- Backfill and update those queries with additional data
- Collect conversation threads and quote tweets of focal event tweets
- Retrieve full user timelines for any user tweeting during a focal event

All of these functionalities are _easy, single line commands_, rather than long multi-line scripts, as are typically needed to read IDs, query the API, output data, and merge it with existing data. This allows researchers to design more complex studies of social media data, and spend more time focusing on data analysis, rather than data storage and maintenance.

## Installation and Documentation

The repository's code can be downloaded directly from Github, or cloned using git:

```
git clone https://github.com/ryanjgallagher/focalevents
```

See the [full documentation]() for more information about installing, configuring, and using the `focalevent` tools.


## A Note

The code here is written and maintained by a single person. First and foremost, it has been designed to help them manage their own data and create replicable pipelines. They are sharing it in the hope that it may help others who have similar workflows and are interested in organizing their Twitter data according to focal events using PostgreSQL.

Requests for enhancements or additions to the code will likely be declined if the author does not anticipate using them in their own research. It is highly unlikely that the code will ever be adapted to work with databases other than PostgreSQL. Further, general problems with database setup or conflicts with pre-existing database structures are beyond the scope of this project and will not be addressed.
