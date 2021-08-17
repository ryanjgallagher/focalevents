import os
import sys
import yaml
import psycopg2
import argparse


def main(config_f='config.yaml'):
    """
    Initializes the directory structure and PostgreSQL database tables for
    collecting social media event data

    1. Creates directories for input (query rules), using the `input.platform`
       fields in the config file
    2. Creates directories for output (raw JSON returned by the API), using the
       `output.json.platform` fields in the config file
    3. Creates a schema and tables for storing the event data using the
       `output.psql.platform` fields in the config.file. The fields of the
       tables and their data types are specified by `insert_fields.platform`.
       The table names should be the same as the keys of `insert_fields.platform`

    NOTE: This configuration script does not create the PostgreSQL database or
    user itself. It assumes that the database has already been properly
    configured and is ready for use

    Parameters
    ----------
    config_f: str
        Filename of the configuration file to use. Defaults to `config.yaml`,
        which assumes that it is in the same directory as where this script is
        being run
    """
    # Load config file
    with open(config_f) as fin:
        config = yaml.load(fin, Loader=yaml.Loader)

    # Setup input and output directories
    for platform in config['input']:
        for query_type in config['input'][platform]:
            dir = config['input'][platform][query_type]
            os.makedirs(dir, exist_ok=True)

    # Setup output directories
    for platform in config['output']['json']:
        for query_type in config['output']['json'][platform]:
            dir = config['output']['json'][platform][query_type]
            os.makedirs(dir, exist_ok=True)

    # Setup schemas and tables
    conn = psycopg2.connect(host=config['psql']['host'],
                            port=config['psql']['port'],
                            user=config['psql']['user'],
                            database=config['psql']['database'],
                            password=config['psql']['password'])
    cur = conn.cursor()

    for platform in config['output']['psql']:
        schema = config['output']['psql'][platform]['schema']
        schema_cmd = f"CREATE SCHEMA IF NOT EXISTS {schema};"
        cur.execute(schema_cmd)

        for insert_type in config['output']['psql'][platform]['tables']:
            table = f"{schema}.{insert_type}"
            insert_field2type = config['insert_fields'][platform][insert_type]
            field_strs = [f"{field} {t}" for field,t in insert_field2type.items()]
            fields_str = ','.join(field_strs)
            fields_str += ", PRIMARY KEY (id, event)"

            create_cmd = f"CREATE TABLE IF NOT EXISTS {table} ({fields_str});"
            cur.execute(create_cmd)

    conn.commit()
    cur.close()
    conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Social media data pipeline config")
    parser.add_argument("-config", type=str, default="config.yaml")
    args = parser.parse_args()

    main(args.config)
