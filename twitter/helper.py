import os
import sys
import json
from dateutil import parser
from datetime import datetime
from psycopg2.extras import Json

# ------------------------------------------------------------------------------
# ------------------------- Database / writing functions -----------------------
# ------------------------------------------------------------------------------
def get_update_cmd(update_fields, query_type, insert_type):
    """
    Creates the update command to use with an insertion to a PostgreSQL database,
    given the fields to be updated

    Parameters
    ----------
    update_fields: list of strs
        Fields that will be updated
    query_type: str
        The type of event query being run: "search", "stream", "convo_search",
        "quote_search" ,or "timeline_search"
    insert_type: str
        The type of insertion being done: "tweets", "users", "media", "places"
    """
    if query_type != 'stream' and insert_type == 'tweets':
        update_fields.append(f"from_{query_type}")
        update_fields.append(f"directly_from_{query_type}")

    update_str = ','.join([f"{f} = EXCLUDED.{f}" for f in update_fields])
    update_cmd = f"DO UPDATE SET {update_str}"
    return update_cmd


def get_insert_cmd(insert_fields, table, update_cmd=None):
    """
    Creates the insert command to use with an insertion to a PostgreSQL database,
    given the table and the fields to be inserted

    Parameters
    ----------
    insert_fields: list of strs
        Fields of data that will be inserted
    table: str
        Name of the table being inserted into
    update_cmd:
        Update command to use when there is a conflict on the ID and event keys.
        If `None`, then defaults to "DO NOTHING" and no update is performed
    """
    if update_cmd is None:
        update_cmd = "DO NOTHING"
    insert_str = ','.join(insert_fields)
    insert_cmd = f"INSERT INTO {table} ({insert_str}) VALUES %s ON CONFLICT (id,event) {update_cmd}"

    json_array_fields = {'urls', 'description_urls'}
    template_strs = []
    for f in insert_fields:
        if f in json_array_fields:
            s = f"%({f})s::jsonb[]"
        else:
            s = f"%({f})s"
        template_strs.append(s)
    template_str = ','.join(template_strs)
    template = f"({template_str})"

    return insert_cmd,template


# ------------------------------------------------------------------------------
# ---------------------------- Extraction functions ----------------------------
# ------------------------------------------------------------------------------
def get_all_inserts(tweets, includes, event, query_type):
    """
    Gets all the data for insertion into a PostgreSQL database from a set of
    tweets. This includes insertion data for the tweets, the tweets' authors,
    any referenced tweets among all those tweets, the authors of those
    referenced tweets, any media in the tweets, and any place data linked to the
    tweets

    Note: We can get information about referenced tweets for a tweet directly
    from a query, but not reference information of tweets referenced by those
    referenced tweets (the reference data is not recursive with each call)

    Parameters
    ----------
    tweets: list of Twitter dict objects
        A list of tweet dict objects to extract insertion data from. This should
        come from the `data` field of the API's response
    includes: dict of lists of dict objects
        The `includes` field of the API's response. Potentially contains the
        fields `media`, `tweets`, `users`, and `places`. Represents all the
        referenced data, users, and places in the tweets in the response
    event: str
        Event name of the query
    query_type: str
        The type of API query: either "stream", "search", "convo_search", or
        "timeline_search"

    Returns
    -------
    tweet_inserts, ref_inserts, user_inserts, media_inserts, place_inserts: lists of dicts
        Lists of dictionaries that contain the insertion data. There is one list
        each for tweets originally from the query, tweets referenced by those in
        the query, all authors of both those sets of tweets, any media
        referenced in those tweets, and any places data linked to those tweets
    """
    # Get referenced tweet info about authors
    ref_id2author_id,author_id2n_followers,handle2author_id = get_author_data(includes)
    author_id2handle = {a_id:handle for handle,a_id in handle2author_id.items()}
    tweet_id2ref_type2author,tweet_id2ref_type2n_followers = (
        get_ref_relations(tweets, ref_id2author_id, author_id2n_followers, author_id2handle)
    )

    # Get insert data for tweets directly from search / stream
    tweet_ids = set()
    tweet_inserts = []
    for tweet in tweets:
        # Get basic insertation data of tweet
        tweet_insert = get_tweet_insert(tweet, event, query_type, direct=True)
        tweet_id = tweet['id']
        tweet_ids.add(tweet_id)
        # Update with mentioned users
        try:
            mentioned = [m['tag'] for m in tweet['entities']['mentions']]
            mentioned_author_ids = [handle2author_id[h] for h in mentioned]
            tweet_insert['mentioned_handles'] = mentioned
            tweet_insert['mentioned_author_ids'] = mentioned_author_ids
        except KeyError:
            tweet_insert['mentioned_handles'] = None
            tweet_insert['mentioned_author_ids'] = None
        # Update with other info
        tweet_insert['author_handle'] = author_id2handle[tweet['author_id']]
        tweet_insert['author_follower_count'] = author_id2n_followers[tweet['author_id']]
        # Update with information about all of its referenced authors
        ref_type2author = tweet_id2ref_type2author[tweet_id]
        ref_type2n_followers = tweet_id2ref_type2n_followers[tweet_id]
        ref_authors_insert = update_w_ref_author_data(ref_type2author, ref_type2n_followers)
        tweet_insert.update(ref_authors_insert)
        tweet_inserts.append(tweet_insert)

    # Get insert data for referenced tweets
    ref_inserts = []
    if 'tweets' in includes:
        for tweet in includes['tweets']:
            if tweet['id'] in tweet_ids:
                # Don't make duplicate inserts for efficency
                continue
            ref_insert = get_tweet_insert(tweet, event, query_type, direct=False)
            try:
                mentioned = [m['tag'] for m in tweet['entities']['mentions']]
                mentioned_author_ids = [handle2author_id[h] for h in mentioned]
                ref_insert['mentioned_handles'] = mentioned
                ref_insert['mentioned_author_ids'] = mentioned_author_ids
            except KeyError:
                ref_insert['mentioned_handles'] = None
                ref_insert['mentioned_author_ids'] = None
            ref_insert['author_handle'] = author_id2handle[tweet['author_id']]
            ref_insert['author_follower_count'] = author_id2n_followers[tweet['author_id']]
            ref_inserts.append(ref_insert)

    # Get insert data for users
    user_inserts = []
    for user in includes['users']:
        user_insert = get_user_insert(user, event)
        user_inserts.append(user_insert)

    # Get media inserts
    media_inserts = []
    if 'media' in includes:
        seen_ids = set()
        for media in includes['media']:
            media_insert = get_media_insert(media, event)
            # Not sure why this is necessary but `includes` can have duplicate
            # entries for media? Which messes up DB insertion. Might have
            # somthing to do with different view_counts
            if media_insert['id'] in seen_ids:
                continue
            else:
                seen_ids.add(media_insert['id'])

            media_inserts.append(media_insert)

    # Get place inserts
    place_inserts = []
    if 'places' in includes:
        for place in includes['places']:
            place_insert = get_place_insert(place, event)
            place_inserts.append(place_insert)

    return tweet_inserts,ref_inserts,user_inserts,media_inserts,place_inserts


def get_author_data(includes):
    """
    Gets the authors of the referenced tweets, and the number of followers of
    all authors

    Parameters
    ----------
    includes: dict of lists of dict objects
        The `includes` field of the API's response. Potentially contains the
        fields `media`, `tweets`, `users`, and `places`. Represents all the
        referenced data, users, and places in the tweets in the response

    Returns
    -------
    ref_id2author_id: dict
        Dictionary mapping tweet IDs of referenced tweets to their author IDs
    author_id2n_followers: dict
        Dictionary mapping author IDs (of all returned search tweets and their
        referened tweets) to their number of followers
    handle2author_id:dict
        Dictionary mapping user handles to their author IDs
    """
    # Get ref tweet -> author, user -> n followers ahead of time for efficiency
    author_id2n_followers = {u['id']:u['public_metrics']['followers_count']
                             for u in includes['users']}
    handle2author_id = {u['username']:u['id'] for u in includes['users']}
    if 'tweets' in includes:
        ref_id2author_id = dict()
        for r in includes['tweets']:
            try:
                ref_id2author_id[r['id']] = r['author_id']
            except KeyError:
                # Note: you can have a referenced tweet that's not included if
                # the author of the included tweet has their profile set to
                # private. In that case just skip adding the referenced tweet
                # details
                continue
    else:
        ref_id2author_id = dict()

    return ref_id2author_id, author_id2n_followers, handle2author_id


def get_ref_relations(tweets, ref_id2author_id, author_id2n_followers,
                      author_id2handle):
    """
    For each tweet, parse its referenced tweets and get the type of reference,
    the referenced author, and that author's number of followers. This is used
    to augment tweet objects that come directly from a query

    Note: the ID of a referenced tweet and its relationship to the original
    tweet is included in the original tweet's object, so we don't need to get
    it here

    Parameters
    ----------
    tweets: list of Twitter dict objects
        A list of tweets to augment with relational data. This should come from
        the `data` field of the API's response
    ref_id2author_id: dict
        Dictionary mapping tweet IDs of referenced tweets to their author IDs
    author_id2n_followers: dict
        Dictionary mapping author IDs (of all returned tweets and their
        referened tweets) to their number of followers
    author_id2handle:
        Dictionary mapping author IDs (of all returned tweets and their
        referenced tweets) to handles

    Returns
    -------
    tweet_id2ref_type2author: dict
        Dictionary where keys are tweet IDs of tweets directly from the query
        and values are dictionaries where keys are types of reference tweets
        (e.g. "quoted") and values are a tuple of the corresponding author ID
        and handle of the tweet that was referenced in that way
    tweet_id2ref_type2n_followers: dict
        Dictionary where keys are tweet IDs of tweets directly from the query
        and values are dictionaries where keys are types of reference tweets
        (e.g. "quoted") and values are the number of followers of the
        corresponding author of the tweet that was referenced in that way
    """
    # Get information of referenced authors and their relation to original tweet
    # Note: single user can have multiple relations, e.g. author can self-quote
    tweet_id2ref_type2author = dict()
    tweet_id2ref_type2n_followers = dict()
    for tweet in tweets:
        tweet_id = tweet['id']
        tweet_id2ref_type2author[tweet_id] = dict()
        tweet_id2ref_type2n_followers[tweet_id] = dict()

        if 'referenced_tweets' in tweet:
            # Get referenced tweet relations to the original tweet
            for referenced_tweet in tweet['referenced_tweets']:
                ref_id = referenced_tweet['id']
                ref_type = referenced_tweet['type']
                try:
                    ref_author_id = ref_id2author_id[ref_id]
                    ref_handle = author_id2handle[ref_author_id]
                except KeyError:
                    # Referenced tweet not included if account is private
                    continue
                # Get the author of each referenced tweet
                tweet_id2ref_type2author[tweet_id][ref_type] = (ref_author_id, ref_handle)
                tweet_id2ref_type2n_followers[tweet_id][ref_type] = (
                    author_id2n_followers[ref_author_id]
                )

    return tweet_id2ref_type2author, tweet_id2ref_type2n_followers


def update_w_ref_author_data(ref_type2author, ref_type2n_followers):
    """
    Update a tweet insert with information about its referenced tweets authors

    Parameters
    ----------
    ref_type2author: dict
        Dictionary where keys are types of references made in the tweet
        (e.g. "quoted") and values are tuples of the author IDs and handles of
        the referenced tweets
    ref_type2n_followers: dict
        Dictionary where keys are types of references made in the tweet
        (e.g. "quoted") and values are the number of followers of the authors of
        the referenced tweets
    Returns
    -------
    ref_authors_insert: dict
        Dictionary for updating the referenced authors information of the tweet
        being inserted (e.g. keys like "quoted_author_id" and
        "quoted_follower_count")
    """
    ref_authors_insert = dict()
    for ref,(author_id,handle) in ref_type2author.items():
        ref_authors_insert[f"{ref}_handle"] = handle
        ref_authors_insert[f"{ref}_author_id"] = author_id
        ref_authors_insert[f"{ref}_follower_count"] = ref_type2n_followers[ref]

    return ref_authors_insert


def get_tweet_insert(tweet, event, query_type, direct):
    """
    Gets all the insertion data for a single tweet

    Parameters
    ----------
    tweet: dict
        Dictionary object of a tweet

    Returns
    -------
    tweet_insert: dict
        Dictionary of values extracted and formatted for insertion into a
        PostgreSQL database
    event: str
        Event name of query the tweet was retrieved from
    query_type: str
        The type of query: "search", "stream", "convo_search", or "timeline_search"
    direct: str
        Whether the tweet came directly from the query or not, i.e. is the tweet
        a referenced tweet or not
    """
    # URLs
    try:
        urls = tweet['entities']['urls']
        urls = [json.dumps(url) for url in urls]
    except KeyError:
        urls = None
    # Hashtags
    try:
        hashtags = [hashtag_info['tag'] for hashtag_info in tweet['entities']['hashtags']]
    except KeyError:
        hashtags = None
    # Media
    try:
        media_keys = tweet['attachments']['media_keys']
    except KeyError:
        media_keys = None
    # Place ID
    try:
        place_id = tweet['geo']['place_id']
    except KeyError:
        place_id = None
    # Source
    try:
        source = tweet['source']
    except KeyError:
        source = None
    # Referenced tweets
    ref_tweets = {'replied_to': None, 'quoted': None, 'retweeted': None}
    try:
        ref_tweets.update({r['type']: r['id'] for r in tweet['referenced_tweets']})
    except:
        pass

    now = datetime.now()

    # Set all tweet insertion data
    tweet_insert = {
        'id': tweet['id'],
        'event': event,
        'inserted_at': now,
        'last_updated_at': now,
        'from_search': False,
        'directly_from_search': False,
        'from_stream': False,
        'directly_from_stream': False,
        'from_convo_search': False,
        'directly_from_convo_search': False,
        'from_quote_search': False,
        'directly_from_quote_search': False,
        'from_timeline_search': False,
        'directly_from_timeline_search': False,
        'text': tweet['text'].replace('\x00', ''),
        'lang': tweet['lang'],
        'author_id': tweet['author_id'],
        'created_at': parser.parse(tweet['created_at']),
        'conversation_id': tweet['conversation_id'],
        'possibly_sensitive': tweet['possibly_sensitive'],
        'reply_settings': tweet['reply_settings'],
        'source': source,
        'retweet_count': tweet['public_metrics']['retweet_count'],
        'reply_count': tweet['public_metrics']['reply_count'],
        'like_count': tweet['public_metrics']['like_count'],
        'quote_count': tweet['public_metrics']['quote_count'],
        'hashtags': hashtags,
        'urls': urls,
        'media_keys': media_keys,
        'place_id': place_id,
        'replied_to': ref_tweets['replied_to'],
        'replied_to_author_id': None,
        'replied_to_handle': None,
        'replied_to_follower_count': None,
        'quoted': ref_tweets['quoted'],
        'quoted_author_id': None,
        'quoted_handle': None,
        'quoted_follower_count': None,
        'retweeted': ref_tweets['retweeted'],
        'retweeted_author_id': None,
        'retweeted_handle': None,
        'retweeted_follower_count': None
    }
    tweet_insert[f"from_{query_type}"] = True
    tweet_insert[f"directly_from_{query_type}"] = direct

    return tweet_insert


def get_user_insert(user, event):
    """
    Gets all insertion data for a single user

    Parameters
    ----------
    user: dict
        Dictionary object of a Twitter user
    event: str
        Event name of query the user was retrieved from

    Returns
    -------
    user_insert: dict
        Dictionary of values extracted and formatted for insertion into a
        PostgreSQL database
    """
    # Description hashtags
    try:
        hashtags = [hashtag_info['tag'] for hashtag_info in user['entities']['description']['hashtags']]
    except KeyError:
        hashtags = None
    # Description mentions
    try:
        mentions = [mention_info['tag'] for mention_info in user['entities']['description']['mentions']]
    except KeyError:
        mentions = None
    # Description URLs
    try:
        urls = user['entities']['description']['urls']
        urls = [json.dumps(url) for url in urls]
    except KeyError:
        urls = None
    # Profile URL
    try:
        url = user['entities']['url']['urls'][0]['expanded_url']
    except (KeyError, IndexError):
        url = None

    now = datetime.now()

    user_insert = {
        'id': user['id'],
        'event': event,
        'inserted_at': now,
        'last_updated_at': now,
        'name': user['name'],
        'username': user['username'],
        'created_at': user['created_at'],
        'followers_count': user['public_metrics']['followers_count'],
        'following_count': user['public_metrics']['following_count'],
        'tweet_count': user['public_metrics']['tweet_count'],
        'url': url,
        'profile_image_url': user['profile_image_url'],
        'description_urls': urls,
        'description_hashtags': hashtags,
        'description_mentions': mentions,
        'verified': user['verified']
    }

    for f in ['description', 'location', 'pinned_tweet_id']:
        try:
            user_insert[f] = user[f].replace('\x00', '')
        except KeyError:
            user_insert[f] = None

    return user_insert


def get_media_insert(media, event):
    """
    Gets all insertion data for a single media object

    Parameters
    ----------
    media: dict
        Dictionary object of a media object
    event: str
        Event name of query the media was retrieved from

    Returns
    -------
    media_insert: dict
        Dictionary of values extracted and formatted for insertion into a
        PostgreSQL database
    """
    # Duration
    try:
        duration_ms = media['duration_ms']
    except KeyError:
        duration_ms = None
    # View count
    try:
        view_count = media['public_metrics']['view_count']
    except KeyError:
        view_count = None
    # Preview
    try:
        preview_url = media['preview_image_url']
    except KeyError:
        preview_url = None

    now = datetime.now()

    media_insert = {
        'id': media['media_key'],
        'event': event,
        'inserted_at': now,
        'last_updated_at': now,
        'type': media['type'],
        'duration_ms': duration_ms,
        'height': media['height'],
        'width': media['width'],
        'preview_image_url': preview_url,
        'view_count': view_count
    }

    return media_insert


def get_place_insert(place, event):
    """
    Gets all insertion data for a single place object

    Parameters
    ----------
    place: dict
        Dictionary object of a place object
    event: str
        Event name of query the place was retrieved from

    Returns
    -------
    place_insert: dict
        Dictionary of values extracted and formatted for insertion into a
        PostgreSQL database
    """

    now = datetime.now()

    place_insert = {
        'id': place['id'],
        'event': event,
        'inserted_at': now,
        'last_updated_at': now,
        'name': place['name'],
        'full_name': place['full_name'],
        'country': place['country'],
        'country_code': place['country_code'],
        'geo': Json(place['geo']),
        'place_type': place['place_type']
    }

    return place_insert
