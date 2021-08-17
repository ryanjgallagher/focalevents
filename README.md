# Social Media Focal Events

The `focalevents` repository makes advanced studies of social media data easier by providing tools that manage the storage and augmentation of data collected around a particular focal event or query.

It is often difficult to organize data from different API queries. For example, we may collect tweets when a hashtag starts trending by using Twitter's filter stream. Later, we may mak separate query to the search endpoint backfill our stream with what we missed before we started it, or update it with tweets that occurred since we stopped the stream. We may also want to get reply threads, quote tweets, or user timelines related to the hashtag's tweets. Each of these datasets is related to a focal event---the hashtag---but they require separate calls to the API. So if thought isn't given beforehand to how the data will be stored, it is easy for these multiple API queries to result in many disjoint files. This makes it difficult to organize, merge, update, backfill, and preprocess them quickly and reliably.

The `focalevents` codebase organizes social media focal event data using PostgreSQL, making it easy to query, backfill, update, sort, and augment the data. For example, collecting Twitter conversations, quotes, or user timelines are all _easy, single line_ commands using `focalevents`, instead of multi-line scripts that need to read IDs, query the API, and output the data. This allows researchers to design more complex studies of social media data and spend more time focusing on data analysis than data storage and maintenance.

Currently, `focalevents` can be used to collect data from Twitter using the v2 API with academic credentials.

## Getting Started

### Installation

The repository's code can be downloaded directly from Github, or cloned using git:

```
git clone https://github.com/ryanjgallagher/focalevents
```

You will also need to install PostgreSQL and create a database on the computer that you want to run this code. There are many online resources for installing PostgreSQL and configuring a database, so there are no utilities or instructions here for doing so.


### Configuration

The configuration file `config.yaml` specifies important information for connecting to different APIs and storing the data. Some of these fields need to be set before starting. Directories, schemas, and tables do not have to already exist when you are specifying them in the configuration file; `config.py` will create them as necessary. The only thing that needs to already exist is the PostgreSQL database.

1. Under the `psql` field, you need to provide information for connecting to the database. At minimum, you need to specify the `database` name and `user` name. If you have altered any of the PostgreSQL defaults, you may also need to enter the `host`, `port`, or `password`. Otherwise, these can be left as `null`.

2. Under `keys`, you need to provide API authorization tokens.

3. Individual event query configuration files are used to set the queries sent to the API (see below for more detail). The `input` field specifies the directories from which those files will be read. This directory defaults to `input` in the `focalevents` directory, but it can be changed to any other directory.

4. Data is stored both in a PostgreSQL database and as raw JSON. The schema and tables used for storing the data in PostgreSQL can be set using the `output.psql` fields. The schema can be changed, but it is suggested to not change the table names from the defaults. For the JSON output, the `output.json` field specifies the directories where the raw JSON will be written. This directory defaults to `output` in the `focalevents` directory, but it can be changed to any other directory.

Once the database information, API tokens, and input and output locations are set, go to the `focalevents` folder and run:

```
python config.py
```

## Usage

### Creating a Query





### Getting Focal Event Data

Once the focal event's query configuration file is set, you are ready to run it. All queries are

1. Run using Python at the command line using the `-m` option

2. Run from the `focalevents` directory

3. Specified using the event name used to name the configuration file

If the event's name is `facebook_oversight`, then we can run a basic Twitter search by going to the`focalevents` directory and entering:

```
python -m twitter.search facebook_oversight
```

For details on what tools and options are available for Twitter specifically and examples of how to use them, see [here]().
