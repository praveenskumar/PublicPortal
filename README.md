

# Requirements

1. python 2.7
1. Postgres

# Installation

### Python Environment

1. Clone this repo from github.
1. Create virtual environment (*portal* as our example): `mkvirtualenv portal`
1. Install requirements.txt into the *portal* enviroment: `pip install -r whalesmediaportal/requirements.txt`

### Database

1. Install Postgres locally (for mac users, try https://postgresapp.com)
1. Create `portal` in your local database
1. Download database file from admin (assume filename = database.postgres)
1. `python whalesmediaportal/database.py database.postgres` to install the database

# Development

1. `python manage.py runserver` to run

# Testing

1. `export FLASK_APP=portal/run.py`
1. `python -m unittest discover`

# Translation
- `pybabel extract -F portal/translations/babel.cfg -k _gettext -k _ngettext -k lazy_gettext -o portal/translations/messages.pot .`

- (subsequent time) `pybabel update -i portal/translations/messages.pot -d portal/translations/`
	- (first time) `pybabel init -i portal/translations/messages.pot -d portal/translations/translations -l zh`

- edit the messages.po file, `open portal/translations/zh/LC_MESSAGES/messages.po`

- `pybabel compile -d portal/translations/`

# Deployment to Heroku

- `heroku config:set HEROKU=1`
- `heroku config:set FLASK_APP=portal/run.py`
- `heroku run flask db upgrade`
- `heroku run python manage.py initdb`

# Restoring to Heroku

- `pg_restore  -d portal ~/Desktop/portal_vendors2.dump` Download to local
- `pg_dump -Fc --no-acl --no-owner -h localhost portal > portal.dump`
- `heroku pg:backups:restore --verbose 'https://s3-us-west-1.amazonaws.com/adalvknsdlkvnalsdkv/portal.dump' DATABASE_URL`
- **Make sure you press ENTER a few times because the prompt is flakey**

# Modifying Enum

- Try this locally using `CREATE DATABASE portal TEMPLATE portal_old;`

- For migrations, I have chosen to *not create a new script* but *to modify the
  init script* directly. This is because the schema will be not be compatible with your codebase anyway.

```
ALTER TYPE account_status ADD VALUE 'APPEAL_REQUESTED';
ALTER TYPE account_status ADD VALUE 'APPEAL_SUBMITTED';

UPDATE accounts SET status = 'ACTIVE' WHERE status = 'PENDING';
UPDATE accounts SET status = 'APPEAL_REQUESTED' WHERE status = 'APPEAL';
UPDATE accounts_version SET status = 'ACTIVE' WHERE status = 'PENDING';
UPDATE accounts_version SET status = 'APPEAL_REQUESTED' WHERE status = 'APPEAL';

ALTER TYPE account_status RENAME TO account_status_old;

CREATE TYPE account_status AS ENUM('ABANDONED', 'ACTIVE', 'APPEAL_REQUESTED', 'APPEAL_SUBMITTED', 'ATTENTION', 'DISAPPROVED', 'RESERVED', 'SUSPENDED', 'UNASSIGNED', 'UNINITIALIZED');

ALTER TABLE accounts ALTER COLUMN status TYPE account_status USING status::text::account_status;
ALTER TABLE accounts_version ALTER COLUMN status TYPE account_status USING status::text::account_status;

DROP TYPE account_status_old;
```

