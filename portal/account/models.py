# -*- coding: utf-8 -*-

import enum
import math

import sqlalchemy
from flask_admin.babel import gettext
from flask_babelex import lazy_gettext
from portal.cache import cache
from portal.models import db
from portal.permission.models import Permission
from portal.user import RolesEnum
from portal.utils import ranges
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import expression, func

u = lambda s: unicode(s, 'utf-8')       # noqa


association_table = db.Table(
    'account_vps',
    db.Column('account_id', db.Integer, db.ForeignKey('accounts.id')),
    db.Column('vps_id', db.Integer, db.ForeignKey('vps.id'))
)


class AccountStatus(enum.Enum):
    UNINITIALIZED = 'uninitialized'
    UNASSIGNED = 'unassigned'
    RESERVED = 'reserved'
    ATTENTION = 'attention'
    APPEAL_REQUESTED = 'appeal_requested'
    APPEAL_SUBMITTED = 'appeal_submitted'
    ACTIVE = 'active'
    DISAPPROVED = 'disapproved'
    SUSPENDED = 'suspended'
    ABANDONED = 'abandoned'


class _AccountStatusHelper(object):

    def __init__(self):
        self.unactivated_statuses = [AccountStatus.UNINITIALIZED,
                                     AccountStatus.UNASSIGNED,
                                     AccountStatus.RESERVED]

        self.bulk = [
            (AccountStatus.ATTENTION, u('0_Attention_注意'),
             gettext('Account requires attention. Do Not Use.')),
            (AccountStatus.APPEAL_REQUESTED, u('1_Appeal-Requested_申述请求'),
             gettext('Client requested this account to be appealed.')),
            (AccountStatus.APPEAL_SUBMITTED, u('2_Appeal-Submitted_申述已提交'),
             gettext('Appeal has been submitted.')),
            (AccountStatus.UNINITIALIZED, u('3_Uninitialized_没准备'),
             gettext('Account is not ready')),
            (AccountStatus.UNASSIGNED, u('4_Unassigned_新号'),
             gettext('Account is free for use for anyone')),
            (AccountStatus.RESERVED, u('5_Reserved_已分配'),
             gettext('Account is already assigned to someone. However, this account has <b>NOT</b> been accessed yet. In the event of an emergency, you may reassign this to somebody else.')), # noqa
            (AccountStatus.ACTIVE, u('6_Active_现行'),
             gettext('Account has ad approved and is spending.')),
            (AccountStatus.DISAPPROVED, u('7_Disapproved_不通过'),
             gettext('Account has ad disapproved.')),
            (AccountStatus.ABANDONED, u('8_Abandoned_废弃'),
             gettext('We no longer want to deal with this account anymore.')),
            (AccountStatus.SUSPENDED, u('9_Suspended_挂号'),
             gettext('Account is suspended.')),
        ]

        self.mapping = dict()
        self.reverse_mapping = dict()
        for value, label, desc in self.bulk:
            self.mapping[value] = label
            self.reverse_mapping[label] = value

    def translate(self, status):
        return self.mapping[status]

    def get_value(self, label):
        if not isinstance(label, unicode):
            raise TypeError('You must supply unicode instances to this method')
        return self.reverse_mapping[label]

    def iterall(self):
        return self.bulk

    def iternew(self):
        """Returns iterator for AccountStatus that are applicable to NEW accounts.
        """
        for value, label, desc in self.iterall():
            if value in [AccountStatus.UNINITIALIZED, AccountStatus.UNASSIGNED,
                         AccountStatus.RESERVED, AccountStatus.ACTIVE]:
                yield value, label, desc

    def is_activated(self, account):
        return account.status not in self.unactivated_statuses


AccountStatusHelper = _AccountStatusHelper()        # Singleton


def no_none(*args):
    return all(v is not None for v in args)


class Account(db.Model):
    __tablename__ = 'accounts'
    __versioned__ = {
        'exclude': ['VPSs']
    }

    id = db.Column(db.Integer, primary_key=True)

    status = db.Column(db.Enum(AccountStatus, name='account_status'),
                       nullable=False, default=AccountStatus.UNINITIALIZED)
    adwords_id = db.Column(db.String(20), nullable=False, unique=True)
    nickname = db.Column(db.String(48))

    account_budget = db.Column(db.Float())
    account_budget_override = db.Column(db.Float())
    remaining_account_budget = db.Column(db.Float())
    remaining_account_budget_override = db.Column(db.Float())

    daily_budget = db.Column(db.Float())
    currency = db.Column(db.String(12))
    exchange_rate = db.Column(db.Float())
    is_unlimited = db.Column(db.Boolean(), server_default=expression.false(),
                             default=False)

    login = db.Column(db.String(48))
    password = db.Column(db.String(48))

    batch = db.Column(db.String(48))
    country = db.Column(db.String(24))
    external_comment = db.Column(db.Text())
    internal_comment = db.Column(db.Text())
    auto_tag_on = db.Column(db.Boolean(), default=False)

    VPSs = db.relationship("Vps",
                           secondary=association_table,
                           back_populates="accounts")

    client_id = db.Column(db.Integer(), db.ForeignKey('users.id', onupdate="cascade"))
    client = db.relationship('User', back_populates='accounts')

    vendor_id = db.Column(db.Integer(), db.ForeignKey('vendors.id', onupdate="cascade"))
    vendor = db.relationship('Vendor', back_populates='accounts')

    accesses = db.relationship('Access', back_populates='account')

    # We still need this for sorting
    updated_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now(), onupdate=func.now())

    last_visited_by_eve = db.Column(db.DateTime(timezone=True))

    def __str__(self):
        if self.adwords_id:
            return self.adwords_id
        return 'Empty Account'

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, self.id)

    def get_account_budget(self):
        if self.account_budget_override is not None:
            return self.account_budget_override
        return self.account_budget

    def get_remaining_account_budget(self):
        if self.remaining_account_budget_override is not None:
            return self.remaining_account_budget_override
        return self.remaining_account_budget

    @hybrid_property
    def days_left(self):
        """Returns the number of days left before the budget exhausts.

        Finance dept sorts by days_left asc to alert us so that they can alert us
        which accounts that are running out of money.    For accounts with budget=0
        or empty, we do not want to see them there so we will return a large
        number, i.e. 99.
        """
        if no_none(self.get_remaining_account_budget(), self.daily_budget) \
                and self.daily_budget:
            return math.floor(self.get_remaining_account_budget() / self.daily_budget)
        else:
            return 99

    @days_left.expression
    def days_left(cls):
        return sqlalchemy.func.floor(cls.remaining_account_budget / (cls.daily_budget + 1))  # hack

    @property
    def percentage_spent(self):
        ab, rab = self.get_account_budget(), self.get_remaining_account_budget()
        if no_none(ab, rab) and ab:
            return 100 * (ab - rab) / ab

    @property
    def spent(self):
        ab, rab = self.get_account_budget(), self.get_remaining_account_budget()
        if no_none(ab, rab):
            return ab - rab

    @hybrid_property
    def spent_in_hkd(self):
        if no_none(self.spent, self.exchange_rate):
            return self.spent * self.exchange_rate
        return 0

    @spent_in_hkd.expression
    def spent_in_hkd(cls):
        return (cls.account_budget - cls.remaining_account_budget) * cls.exchange_rate

    @property
    def daily_budget_in_hkd(self):
        if no_none(self.daily_budget, self.exchange_rate):
            return self.daily_budget * self.exchange_rate

    @property
    def remaining_in_hkd(self):
        if no_none(self.get_remaining_account_budget(), self.exchange_rate):
            return self.get_remaining_account_budget() * self.exchange_rate

    @property
    @cache.memoize()
    def days_to_topup(self):
        """Rather than using inline model form, just reflect this
        """
        return self.vendor.days_to_topup

    @property
    @cache.memoize()
    def suspended_on(self):
        """Returns a dt for when suspension occurs. If account is not suspended return None.
        """
        for v in self.versions:
            if v.status == AccountStatus.SUSPENDED:
                return v.updated_at

    @property
    def clients_allowed(self):
        """Returns a string which shows which clients are allowed.

        Not memoizing here because this could be used by other widgets. So it makes sense to use
        cache_helper as we are sharing this between different classes.
        """
        key = 'clients_allowed-%s' % self.vendor_id
        if self.vendor:
            ret = cache.get(key)
            if not ret:
                pems = Permission.query.filter(
                    Permission.vendor_id == self.vendor_id).order_by(Permission.user_id)
                if pems.count():
                    ret = ranges([p.user_id for p in pems])
                else:
                    ret = lazy_gettext("Vendor permissions not defined.")
                cache.set(key, ret)
            return ret
        return lazy_gettext("Vendor is empty.")

    @property
    @cache.memoize()
    def VPSs_jinja(self):
        """Show only AWS VPSs if there are multiple VPSs.
        """
        VPSs = self.VPSs
        has_aws_vps = False
        pos_aws_vps = 0

        for i, vps in enumerate(VPSs):
            if vps.provider and vps.provider.upper().startswith('AWS'):
                has_aws_vps = True
                pos_aws_vps = i
                break

        if has_aws_vps:
            return str(VPSs[pos_aws_vps])
        else:
            return ", ".join(sorted([str(v) for v in VPSs]))

    @property
    @cache.memoize()
    def created_at(self):
        """Running this operation even after memoization has caused the request to take longer than
        30 seconds. Hence, we will only execute this method on the relevant vendors.
        """
        VENDORS = [40, 41, 42]
        if self.vendor_id in VENDORS:
            return self.versions.first().transaction.issued_at.strftime('%m/%d %H:%M')
        return ""


A = RolesEnum.ADMIN.value
T = RolesEnum.TECHNICIAN.value
S = RolesEnum.SUPPORT.value
C = RolesEnum.CLIENT.value


class AttributeMeta(object):
    def __init__(self, priority, label=None, readable=[], editable=[],
                 is_list_editable=False, hide_in_list_view=False):
        self.priority = priority
        self.label = label
        self.readable = readable
        self.editable = editable
        self.is_list_editable = is_list_editable
        self.hide_in_list_view = hide_in_list_view


class AttributeManager(object):
    def __init__(self):
        self.attribute_metas = {
            'adwords_id': AttributeMeta(100, gettext('Adwords_id'),
                                        readable=[A, T, S, C], editable=[A, T, S, C]),
            'nickname': AttributeMeta(120, gettext('Nickname'),
                                      readable=[A, T, S, C], editable=[A, T, S, C]),
            'status': AttributeMeta(130, gettext('Status'),
                                    readable=[A, T, S, C], editable=[A, T, S, C],
                                    is_list_editable=True),

            # editable must be []. If not, last_visited_by_eve will be set by the form
            # which DROPS the timezone thus resulting in an time offset error
            'last_visited_by_eve': AttributeMeta(140, gettext('Last Visited by Eve'),
                                                 readable=[A, T, S, C], editable=[]),

            'client_id': AttributeMeta(200, gettext('Client ID'),
                                       readable=[A, T, S]),
            'client': AttributeMeta(210, gettext('Client Name'),
                                    readable=[A, T, S], editable=[A, T, S]),
            'clients_allowed': AttributeMeta(211, gettext('Clients Allowed'),
                                             readable=[A, C, T, S], editable=[]),

            'auto_tag_on': AttributeMeta(220, gettext('Is auto_tag ON?'),
                                         readable=[A, T, S, C], editable=[A, T]),

            'is_unlimited': AttributeMeta(305, gettext('Is Unlimited?'),
                                          readable=[A, S, C], editable=[A, T]),

            'created_at': AttributeMeta(309, gettext('Creation Date'),
                                        readable=[A], editable=[]),

            'account_budget': AttributeMeta(310, gettext('Account Budget'),
                                            readable=[A, S, C], editable=[A, T],
                                            is_list_editable=True),
            'account_budget_override': AttributeMeta(311, gettext('Account Budget Override'),
                                                     readable=[A, S, C], editable=[A],
                                                     is_list_editable=True),
            'remaining_account_budget': AttributeMeta(320, gettext('Remaining Account Budget'),
                                                      readable=[A, S, C], editable=[A],
                                                      is_list_editable=True),
            'remaining_account_budget_override': AttributeMeta(321, gettext('Remaining Account Budget Override'),  # noqa
                                                               readable=[A, S, C], editable=[A],
                                                               is_list_editable=True),
            'daily_budget': AttributeMeta(330, gettext('Daily Budget'),
                                          readable=[A, S, C], editable=[A],
                                          is_list_editable=True),
            'percentage_spent': AttributeMeta(340, gettext('Percentage Spent'),
                                              readable=[A, S, C], editable=[]),
            'days_left': AttributeMeta(350, gettext('Days Left'),
                                       readable=[A, S, C], editable=[]),
            'currency': AttributeMeta(360, gettext('Currency'),
                                      readable=[A, S, C], editable=[A, T]),
            'exchange_rate': AttributeMeta(370, gettext('Exchange Rate'),
                                           readable=[A, S, C], editable=[A, T],
                                           is_list_editable=True),

            'spent': AttributeMeta(380, gettext('Spent'),
                                   readable=[A, S, C], editable=[]),
            'spent_in_hkd': AttributeMeta(390, gettext('Spent (HKD)'),
                                          readable=[A, S, C], editable=[]),
            'remaining_in_hkd': AttributeMeta(399, gettext('Remaining (HKD)'),
                                              readable=[A, S, C], editable=[]),

            'vendor_id': AttributeMeta(400, gettext('Vendor'),
                                       readable=[A], editable=[A, T],
                                       hide_in_list_view=True),
            'vendor': AttributeMeta(401, gettext('Vendor'),
                                    readable=[A], editable=[A, T]),
            'days_to_topup': AttributeMeta(402, gettext('Days To Topup'),
                                           readable=[A], editable=[]),

            'batch': AttributeMeta(410, gettext('Batch'),
                                   readable=[A, T], editable=[A, T]),

            'VPSs': AttributeMeta(500, gettext('VPS'),
                                  readable=[A, T], editable=[A, T]),
            'login': AttributeMeta(520, gettext('Login'),
                                   readable=[A, T], editable=[A, T]),
            'password': AttributeMeta(522, gettext('Password'),
                                      readable=[A, T], editable=[A, T]),

            'external_comment': AttributeMeta(998, gettext('External Comment'),
                                              readable=[], editable=[]),
            'internal_comment': AttributeMeta(999, gettext('Internal Comment'),
                                              readable=[A, T, S], editable=[A, T, S]),
        }

        self._cache = {}

    def _get_all_columns(self, attr, role, skip=[], is_list_view=False):
        """Returns ALL the column names that this role can read
        """
        cols = {}     # { name: priority },
        for name, meta in self.attribute_metas.iteritems():
            roles = getattr(meta, attr)

            if role not in roles:
                continue

            if is_list_view and meta.hide_in_list_view:
                continue

            if name in skip:
                continue

            cols[name] = meta.priority

        cols_sorted = sorted(cols.iteritems(), key=lambda t: t[1])
        return [t[0] for t in cols_sorted]

    def get_all_readable_columns(self, role):
        key = 'get_all_readable_columns-%s' % role
        if key not in self._cache:
            self._cache[key] = self._get_all_columns('readable', role)
        return self._cache[key]

    def get_all_editable_columns(self, role):
        key = 'get_all_editable_columns-%s' % role
        if key not in self._cache:
            self._cache[key] = self._get_all_columns('editable', role, skip=['vendor_id'])
        return self._cache[key]

    def get_list_view_columns(self, role):
        key = 'get_list_view_columns-%s' % role
        if key not in self._cache:
            self._cache[key] = self._get_all_columns('readable', role, is_list_view=True)
        return self._cache[key]

    def get_list_view_editable_columns(self, role):
        def _work():
            list_editables = set()
            for name, meta in self.attribute_metas.iteritems():
                if meta.is_list_editable:
                    list_editables.add(name)

            # return the intersection
            editables = self.get_list_view_columns(role)
            return set(editables) & list_editables

        key = 'get_list_view_editable_columns-%s' % role
        if key not in self._cache:
            self._cache[key] = _work()
        return self._cache[key]

    def get_list_view_column_labels(self, role):
        """Returns { name: label }
        """
        def _work():
            ret = {}
            for name, meta in self.attribute_metas.iteritems():
                ret[name] = meta.label
            return ret

        key = 'get_list_view_column_labels-%s' % role
        if key not in self._cache:
            self._cache[key] = _work()
        return self._cache[key]


AttributeManagerSingleton = AttributeManager()
