Streaming Data
==============

Specifying the Rules
--------------------

Filter stream rules are specified in an :ref:`event query file <queries>` according to Twitter's filter stream `syntax rules <https://developer.twitter.com/en/docs/twitter-api/tweets/filtered-stream/integrate/build-a-rule/>`_.

See an example of a filter stream query file `here <https://github.com/ryanjgallagher/focalevents/blob/main/input/twitter/stream/facebook_oversight.yaml/>`_.


Using the Filter Stream
-----------------------

Once the event query file is ready, the command for streaming tweets is

.. code-block:: bash

    python -m twitter.stream event_name

The stream can be cancelled at any time with :code:`CTRL+C`.


Streaming Parameters
--------------------

The stream has several optional parameters. These are specified as flags on the standard stream command, for example:

.. code-block:: bash

    python -m twitter.stream event_name --update_rules -update_interval 10


+--------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter                            | Description                                                                                                                              |
+======================================+==========================================================================================================================================+
| config_f                             | The configuration file to use if not using the default                                                                                   |
+--------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| delete_existing_rules / update_rules | Whether to delete rules that have already been sent to the Twitter API for a previous stream. By default, rules are deleted from the API |
+--------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| append / overwrite                   | Whether to append JSON tweets to an existing file for the event. By default, tweets are appended                                         |
+--------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| verbose / quiet                      | Whether to print information/updates to the console while running the stream. By default, information is printed                         |
+--------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| update_interval                      | How often to print updates of the number of tweets collected, in minutes                                                                 |
+--------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
| dry_run                              | Whether to run a "dry run" of the rules without connecting to the Twitter stream to make sure that they are syntactically valid          |
+--------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------+
