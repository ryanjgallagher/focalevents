Getting Started
===============

Installation
------------

The :code:`focalevents` tools can be downloaded directly from Github, or cloned using git:

.. code-block:: bash

    git clone https://github.com/ryanjgallagher/focalevents

You can install any needed packages by navigating to the project directory and running:

.. code-block:: bash

    pip install -r requirements.txt

You will also need to install PostgreSQL and create a database on the computer that you want to run this code. There are many online resources for installing PostgreSQL and configuring a database, so there are no utilities or instructions here for doing so.

Configuration
-------------

The configuration file :code:`config.yaml` specifies important information for connecting to different APIs and storing the data. Some of these fields need to be set before starting.

1. Under :code:`keys`, you need to provide API authorization tokens. Currently, :code:`focalevents` only supports access to the Twitter API v2 using academic credentials.

2. Under the :code:`psql` field, you can provide information for connecting to the database. This includes the database name, user name, host, port, and password.

3. The code outputs raw JSON to the directories specified under :code:`output.json`. These can be changed from their defaults.

4. The processed and organized data is stored in the PostgreSQL schema and tables specified under :code:`output.psql`. The schema name can be changed from the default. It is not recommended to change the table names, as parts of this codebase may not be robust to those changes.

Once the database information and API tokens are set, go to the :code:`focalevents` project directory and run:

.. code-block:: bash

    python config.py

This will create all of the necessary directories, schemas, and tables needed for reading and writing data.
