import os
import subprocess

from flask import current_app
from flask_script import Manager, Shell

from portal.models import db
from portal.run import app
from portal.user import RolesEnum
from portal.user.models import (Role, User, find_or_create_role,
                                                                find_or_create_user)

manager = Manager(app)
def _make_context():
    return dict(app=app, db=db)
manager.add_command("shell", Shell(make_context=_make_context))


@manager.command
def install():
    """Installs this pacakge for the first time.
    """
    subprocess.call(['pip', 'install', '-e', '.'])


@manager.command
def freeze():
    """`pip freeze` and patches the line from installing this package.
    Pip freeze is causing an issue for this package that is installed
    locally through `pip install -e`.
    """
    out = subprocess.check_output(['pip', 'freeze'])
    l = filter(None, out.split('\n'))

    l2 = []
    for name in l:
        if name.startswith('-e'):
            # Replace '-e git+https://github.com/vincentwhales/Portal.git@hash#egg=portal'
            l2.append('-e .')
        else:
            l2.append(name)

    with open('requirements.txt', 'w') as outf:
        def sortfunc(x):
            if x.startswith('-e'):
                return 0
            if x.startswith('git+'):
                return 1
            if x.startswith('six'):
                return 2
            return 3

        outf.write('\n'.join(sorted(l2, key=sortfunc)))

    app.logger.info('Updated requirements.txt via pip freeze.')


@manager.command
def migrate():
    """Outputs the command to migrate this database.
    """
    print """
Local:
Run `flask db migrate`
Run `flask db upgrade`

Heroku:
heroku config:set FLASK_APP=portal
heroku run flask db migrate
heroku run flask db upgrade
    """


@manager.command
def initdb():
    vincent = find_or_create_user('vincent', 'whalesmedia2017!!', 'Vincent Ng')

    r1 = find_or_create_role(RolesEnum.ADMIN.value)
    find_or_create_role(RolesEnum.SUPPORT.value)
    find_or_create_role(RolesEnum.TECHNICIAN.value)
    find_or_create_role(RolesEnum.CLIENT.value)

    vincent.roles.append(r1)
    db.session.commit()


if __name__ == "__main__":
    if not os.path.exists('./requirements.txt'):
        raise Exception("You must run manage.py in the root directory of portal")
    manager.run()
