import os
from subprocess import PIPE, Popen

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT    # <-- ADD THIS LINE


"""
super ghetto script to run pg_restore.

"""

def exists_db(cur, db_name):
    """Don't care about SQL Injection.
    """
    cmd = "SELECT datname FROM pg_database WHERE datname = '%s'" % db_name
    cur.execute(cmd)
    return bool(cur.fetchall())


def main(db_loc):
    """
    USE SINGLE QUOTES

    - Move the current db portal to portal_old
    - Create new DB
    - import from file
    """
    if not os.path.exists(db_loc):
        raise ValueError("File doesn't exist")

    with psycopg2.connect(database="postgres") as conn:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)        # Required for creating db in transaction bloc

        with conn.cursor() as cur:
            if exists_db(cur, 'portal'):
                print "DB 'portal' exists, renaming"
                if exists_db(cur, 'portal_old'):
                    # TODO name the database to something else rather than dropping;
                    print "DB 'portal_old' exists, dropping"
                    cur.execute("DROP DATABASE portal_old")
                cur.execute('ALTER DATABASE portal RENAME TO portal_old')

            print "Creating DB 'portal'"
            cur.execute("CREATE DATABASE portal;")

    command = ['pg_restore', '-d', 'portal', db_loc]
    p = Popen(command, shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    print "Restore complete."


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print "python database.py <heroku pg_restore file location>"
        exit(1)

    main(sys.argv[1])
