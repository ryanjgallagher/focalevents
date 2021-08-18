# Social Media Focal Events

This repository provides tools that make advanced studies of social media data easier by managing the storage and augmentation of data collected around a particular focal event or query on social media. Currently, `focalevents` supports data collection from Twitter using the v2 API with academic credentials.

It is often difficult to organize data from multiple API queries. For example, we may collect tweets when a hashtag starts trending by using Twitter's filter stream. Later, we may make a separate query to the search endpoint to backfill our stream with what we missed before we started it, or update it with tweets that occurred since we stopped it. We may also want to get reply threads, quote tweets, or user timelines based on the tweets we collected. All of these queries are related to a common focal event—the hashtag—but they require several separate calls to the API. It is easy for these multiple queries to result in many disjoint files, making it difficult to organize, merge, update, backfill, and preprocess them quickly and reliably.

The `focalevents` codebase organizes social media focal event data using PostgreSQL, making it easy to query, backfill, update, sort, and augment the data. For example, collecting Twitter conversations, quotes, or user timelines are all _easy, single line_ commands, instead of a multi-line scripts that need to read IDs, query the API, and output the data. This allows researchers to design more complex studies of social media data, and spend more time focusing on data analysis, rather than data storage and maintenance.

## Getting Started

### Installation

The repository's code can be downloaded directly from Github, or cloned using git:

```
git clone https://github.com/ryanjgallagher/focalevents
```

You will also need to install PostgreSQL and create a database on the computer that you want to run this code. There are many online resources for installing PostgreSQL and configuring a database, so there are no utilities or instructions here for doing so.


### Configuration

The configuration file `config.yaml` specifies important information for connecting to different APIs and storing the data. Some of these fields need to be set before starting.

1. Under the `psql` field, you need to provide information for connecting to the database. At minimum, you need to specify the `database` name and `user` name. If you have altered any of the PostgreSQL defaults, you may also need to enter the `host`, `port`, or `password`. Otherwise, these can be left as `null`.

2. Under `keys`, you need to provide API authorization tokens.

Once the database information and API tokens are set, go to the `focalevents` folder and run:

```
python config.py
```

This will create all of the necessary directories, schemas, and tables needed for reading and writing data.

## Usage

### Creating a Query

**All data is organized around an "event name."** This name should be a unique signifer for the focal event around which want to collect data.

Each query is run using an event query configuration file, which is a YAML file named with the event name. For example, say we want to search for tweets about Facebook's Oversight Board. Then we can name our event `"facebook_oversight"`. The specific queries to the Twitter API are specified the event configuration file `input/twitter/search/facebook_oversight.yaml`.

The format of the `.yaml` event configuration files depends on the platform and the type of query being done. You can find examples in this repository's [input directory](https://github.com/ryanjgallagher/focalevents/tree/main/input). The syntax for Twitter queries follows the API's operators ([stream](https://developer.twitter.com/en/docs/twitter-api/tweets/filtered-stream/integrate/build-a-rule), [search](https://developer.twitter.com/en/docs/twitter-api/tweets/search/integrate/build-a-query))


### Getting Focal Event Data

Once the focal event's query configuration file is set, you are ready to run it! All queries are run using Python at the command line using the `-m` flag. For example, if the event's name is `facebook_oversight`, then we can run a basic Twitter search by going to the`focalevents` directory and entering:

```
python -m twitter.search facebook_oversight
```

For details on collecting Twitter data, see [here](https://github.com/ryanjgallagher/focalevents/tree/main/twitter).
