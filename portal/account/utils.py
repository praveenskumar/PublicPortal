import json

import pytz
from flask import Markup
from flask_admin.babel import lazy_gettext
from portal.account.models import AttributeManagerSingleton as AMS
from portal.account.models import AccountStatus
from sqlalchemy_continuum import Operation


class History(object):
    """A wrapper class to represent an entry for "Change History" of account.details_view
    """
    def render(self):
        """Renders to Jinja.
        """
        raise NotImplementedError()

    def can_render(self):
        raise NotImplementedError()

    def __lt__(self, other):
        return self.datetime < other.datetime


class AccessHistory(History):
    """History implementation for Access class.
    """
    def __init__(self, access):
        self.access = access
        self.datetime = access.created_at.astimezone(pytz.timezone('Asia/Hong_Kong'))

    def can_render(self):
        return True

    def render(self):
        return u"""
        <tr>
            <td>{0}</td>
            <td>{1}</td>
            <td>{2}</td>
        </tr>
        """.format(self.datetime.strftime('%m/%d %H:%M'),
                             self.access.user,
                             lazy_gettext('accessed this account.'))


class VersionHistory(History):
    """A wrapper around version history.

    Converts to human readable format.
    Figures out which attributes are displayable to the current user.
    Renders to Jinja.
    """
    def __init__(self, version, role):
        self.can_render_flag = False
        self.time_str = str()
        self.user = str()
        self.content = str()
        self.set_version(version, role)

    def can_render(self):
        return self.can_render_flag

    def render(self):
        return u"""
        <tr>
            <td>{0}</td>
            <td>{1}</td>
            <td>{2}</td>
        </tr>
        """.format(self.time_str, self.user, self.content)

    def get_display_value(self, obj):
        if isinstance(obj, AccountStatus):
            return Markup('<b>%s</b>' % obj.value.encode('utf-8'))
        return obj        # Don't coerce, let jinja handle it

    def set_version(self, version, role):
        """Returns None if current_user has no access to this version
        """
        modifications = []
        for attr, before_after in version.changeset.iteritems():

            if attr in ['updated_at', 'created_at', 'id', 'password', 'last_visited_by_eve']:
                continue
            if attr not in AMS.get_all_readable_columns(role):
                continue

            before, after = before_after
            before = self.get_display_value(before)
            after = self.get_display_value(after)

            if version.operation_type == Operation.INSERT:
                modifications.append('%s=%s' % (attr, after))
            elif version.operation_type == Operation.UPDATE:
                modifications.append('%s: %s &rarr; %s' % (attr, before, after))        # ->

        if not modifications:
            return

        self.can_render_flag = True

        content = ', '.join(modifications)

        if version.operation_type == Operation.INSERT:
            content = lazy_gettext('created ') + content
        elif version.operation_type == Operation.UPDATE:
            content = lazy_gettext('updated ') + content
        else:
            content = lazy_gettext('deleted.')

        # issued_at is NOT timezone aware
        self.datetime = pytz.utc.localize(version.transaction.issued_at)\
            .astimezone(pytz.timezone('Asia/Hong_Kong'))

        self.time_str = self.datetime.strftime('%m/%d %H:%M')
        self.user = version.transaction.user if version.transaction.user else 'eve'
        self.content = content


class ReplacementBank(object):
    """Maps strings to an id.
    """
    def __init__(self):
        self.counter = 0
        self.mapping = {}
        self.reverse = {}
        self.field_names = ['status', 'vps', 'client' ]

    def get_replacement_id(self, replaceable_str):
        if replaceable_str not in self.mapping:
            self.mapping[replaceable_str] = self.counter
            self.reverse[self.counter] = replaceable_str
            self.counter += 1
        return self.mapping[replaceable_str]

    def dump(self):
        return """replacement_bank = %s;""" % json.dumps(self.reverse)
