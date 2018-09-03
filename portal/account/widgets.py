from collections import defaultdict
from datetime import date, datetime, time, timedelta
from itertools import groupby

import pytz
from flask_babelex import gettext
from flask_user import current_user
from portal.account.models import Account, AccountStatus, no_none
from portal.account.utils import VersionHistory
from portal.models import db
from portal.user import RolesEnum
from portal.user.models import User
from portal.utils import OrderedDefaultDict
from portal.utils.widgets import Widget
from portal.vps.models import Vps
from sqlalchemy import and_, func, or_
from sqlalchemy_continuum import transaction_class, version_class

HKTZ = pytz.timezone('Asia/Hong_Kong')


def debug_dt(message, dt):
    print message, dt.strftime('%m/%d %H:%M %A %Z')


def get_shift_start_dt(lohr, current_dt):
    """
    https://stackoverflow.com/questions/49269997/given-a-list-of-shift-start-times-how-do-you-determine-which-range-a-particular
    """
    try:
        max_hour = max([hr for hr in lohr if current_dt > current_dt.replace(hour=hr, minute=0)])
        return current_dt.replace(hour=max_hour, minute=0)
    except ValueError:
        return (current_dt - timedelta(days=1)).replace(hour=max(lohr), minute=0)


def get_end_of_hkt_today():
    """Return today at 23:59 HKT in UTC.
    """
    todate = date.today()
    ret_hkt = HKTZ.localize(datetime.combine(todate, time(23, 59)))
    ret_utc = ret_hkt.astimezone(pytz.utc)
    return ret_utc


class ExpiringWidget(Widget):

    def get_roles(self):
        return [RolesEnum.ADMIN]

    def get_data(self):
        return Account.query.filter(and_(
            ~Account.status.in_([AccountStatus.SUSPENDED,
                                 AccountStatus.ABANDONED,
                                 AccountStatus.APPEAL_REQUESTED,
                                 AccountStatus.APPEAL_SUBMITTED,
                                 AccountStatus.ATTENTION]),
            Account.is_unlimited == False,      # noqa
            Account.remaining_account_budget.isnot(None),
            Account.daily_budget > 0,
            Account.daily_budget.isnot(None),
            Account.days_left < 3),
        ).all()


class NotUpdatedTodayWidget(Widget):

    def get_roles(self):
        return [RolesEnum.ADMIN, RolesEnum.TECHNICIAN]

    def get_data(self):
        SHIFTS = [4, 11, 10]

        hk_now = datetime.now(HKTZ)
        shift_start = get_shift_start_dt(SHIFTS, hk_now)

        accounts = db.session.query(Account).join((Account.VPSs, Vps)).filter(
            and_(Account.status.in_([AccountStatus.ACTIVE, AccountStatus.DISAPPROVED]),
                 or_(Account.last_visited_by_eve == None,       # noqa
                     Account.last_visited_by_eve < shift_start))
        ).order_by(Vps.name)

        title = gettext('Accounts not updated since: %s' % shift_start.strftime('%m/%d %H:%M %Z'))

        # Group acocunts by login which is by MCC
        ret = OrderedDefaultDict(list)
        for act in accounts:
            ret[act.login].append(act)

        return title, ret


class AttentionWidget(Widget):

    def get_roles(self):
        return [RolesEnum.ADMIN]

    def get_data(self):
        q = Account.query.filter(or_(
            Account.status == AccountStatus.ATTENTION,
            Account.status == AccountStatus.APPEAL_REQUESTED,
            Account.status == AccountStatus.APPEAL_SUBMITTED,
            Account.status == AccountStatus.UNINITIALIZED)
        ).order_by(Account.status)

        return groupby(q, key=lambda a: a.status)


class RecentStatusChangeWidget(Widget):
    def get_roles(self):
        return [RolesEnum.ADMIN]

    def get_data(self):
        """Do not pass AccountVersion objects to jinja because we need
        updated information on each account.

        Return in the order of when the account was suspended DESC.
        """
        AccountVersion = version_class(Account)
        week_ago = datetime.now(pytz.utc) - timedelta(days=7)

        order = []

        account_versions = {}
        for av in AccountVersion.query.filter(and_(
                AccountVersion.status_mod == True,      # noqa
                AccountVersion.updated_at > week_ago,
                AccountVersion.status.in_([AccountStatus.SUSPENDED,
                                           AccountStatus.ATTENTION])
        )).order_by(AccountVersion.updated_at.desc()):
            order.append(av.adwords_id)
            account_versions[av.adwords_id] = av

        accounts = {}
        for account in Account.query.filter(
                Account.adwords_id.in_(account_versions.keys())):
            accounts[account.adwords_id] = account

        for adwords_id in order:
            yield (accounts[adwords_id], account_versions[adwords_id])


class AccountHistoryWidget(Widget):
    """This widget is only for changes that are not updated_at nor last_visited_by_eve.
    """
    def get_roles(self):
        return [RolesEnum.ADMIN, RolesEnum.SUPPORT, RolesEnum.TECHNICIAN]

    def get_data(self):
        Transaction = transaction_class(Account)
        yesterday = datetime.utcnow() - timedelta(days=1)
        trans = Transaction.query.order_by(Transaction.issued_at.desc()) \
            .filter(Transaction.issued_at > yesterday).all()

        AccountVersion = version_class(Account)
        histories = []
        for t in trans:

            # Note that one transaction can have effect on multiple entity
            for av in AccountVersion.query.filter(AccountVersion.transaction_id == t.id):
                history = VersionHistory(av, current_user.roles[0].name)
                has_real_change = set(av.changeset.keys()) != set(['updated_at',
                                                                   'last_visited_by_eve'])
                if has_real_change and history.can_render():
                    histories.append(history)

        return histories


class TotalSpendWidget(Widget):

    def get_roles(self):
        return [RolesEnum.ADMIN]

    def _get_data(self, dt):
        """
        SELECT t.client_id AS accounts_client_id,
                     sum((t.account_budget - t.remaining_account_budget) * t.exchange_rate) AS sum_1
        FROM (
                    SELECT DISTINCT ON (adwords_id) *
                    FROM accounts_version
                    WHERE accounts_version.updated_at < now_utc()
                    ORDER BY accounts_version.adwords_id, accounts_version.updated_at DESC
        ) AS t
        GROUP BY t.client_id ORDER BY t.client_id
        """
        AccountVersion = version_class(Account)

        t = AccountVersion.query.distinct(AccountVersion.adwords_id)\
            .filter(AccountVersion.updated_at < dt)\
            .order_by(AccountVersion.adwords_id, AccountVersion.updated_at.desc())\
            .subquery('t')

        # Have to manually define the hybrid in subqueries
        hyb = func.sum(
            (t.c.account_budget - t.c.remaining_account_budget) * t.c.exchange_rate)

        q = db.session.query(t.c.client_id, hyb).group_by(t.c.client_id)
        return q.all()

    def get_data(self):
        users = []
        for user in User.query.order_by(User.id).all():
            if RolesEnum.CLIENT.value in [role.name for role in user.roles]:
                users.append((user.id, user.name))

        # (user_id, total)
        db.session.query(Account.client_id, func.sum(Account.spent_in_hkd))\
            .group_by(Account.client_id).order_by(Account.client_id).all()

        results = []

        utc_dt = get_end_of_hkt_today()
        for i in xrange(7):
            hk_dt = utc_dt.astimezone(HKTZ)
            t = self._get_data(utc_dt) + [('header', hk_dt.strftime('%m/%d %A'))]
            results.append(dict(t))
            utc_dt = utc_dt - timedelta(days=1)

        return users, list(reversed(results))


class HighSpendWidget(Widget):

    def get_roles(self):
        return [RolesEnum.ADMIN]

    def get_data(self):
        ret = []
        hyb = (Account.account_budget - Account.remaining_account_budget) * Account.exchange_rate

        for account in Account.query.order_by(hyb.desc()):
            if account.spent_in_hkd > 0:
                ret.append(account)
                if len(ret) > 30:
                    break

        return ret


class FakeAccount(object):

    def __init__(self, *args, **kwargs):
        self.adwords_id = kwargs['adwords_id']
        self.daily_budget = kwargs['daily_budget']
        self.spent_in_hkd = kwargs['spent_in_hkd']

    def __repr__(self):
        return '<%s>' % self.adwords_id


class ActiveAccountsWidget(Widget):
    """
    Rather than returning 3 separate objects, we will combine all three into
    one single table now.

    <User 1>
                    2     1     0
    act_1     x     x     x
    act_2     x     x
    act_3     x
    act_4             x     x
    """
    def get_roles(self):
        return [RolesEnum.ADMIN, RolesEnum.SUPPORT]

    def get_dts(self):
        today = get_end_of_hkt_today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)
        return (day_before, yesterday, today)

    def get_data(self):
        """
        We need the following:
        1. users:
        2. actives_0: { adwords_id: fake_account }
        """
        users = {}        # user_id: adwords_ids
        actives_0 = defaultdict(lambda: None)
        actives_1 = defaultdict(lambda: None)
        actives_2 = defaultdict(lambda: None)

        for user in User.query.order_by(User.id).all():
            if RolesEnum.CLIENT.value in [role.name for role in user.roles]:
                users[user.id] = set()

        # actives_0
        for account in Account.query.filter(
                Account.status == AccountStatus.ACTIVE).order_by(Account.adwords_id):

            key = account.adwords_id
            users[account.client_id].add(key)
            actives_0[key] = FakeAccount(adwords_id=key,
                                         daily_budget=account.daily_budget,
                                         spent_in_hkd=account.spent_in_hkd)

        # actives_1, 2
        today = get_end_of_hkt_today()
        yesterday = today - timedelta(days=1)
        day_before = today - timedelta(days=2)

        AccountVersion = version_class(Account)

        def _set(dic, dt):
            """
            SELECT DISTINCT ON (adwords_id) *
            FROM accounts_version
            WHERE accounts_version.updated_at < now_utc()
            AND accounts_version.status = 'ACTIVE'
            ORDER BY accounts_version.adwords_id, accounts_version.updated_at DESC
            """
            query = AccountVersion.query.distinct(AccountVersion.adwords_id)\
                .filter(and_(AccountVersion.updated_at < dt,
                             AccountVersion.updated_at > dt - timedelta(days=1),
                             AccountVersion.status == AccountStatus.ACTIVE))\
                .order_by(AccountVersion.adwords_id, AccountVersion.updated_at.desc())

            for av in query:
                spent_in_hkd = None
                if no_none(av.get_account_budget(),
                           av.get_remaining_account_budget(), av.exchange_rate):
                    spent_in_hkd = av.exchange_rate * \
                        (av.get_account_budget() - av.get_remaining_account_budget())

                key = av.adwords_id
                users[av.client_id].add(key)
                dic[key] = FakeAccount(adwords_id=key,
                                       daily_budget=av.daily_budget,
                                       spent_in_hkd=spent_in_hkd)

        _set(actives_1, yesterday)
        _set(actives_2, day_before)

        ret = {}
        for user_id, adwords_ids in users.iteritems():
            # [adwords_id], [FakeAccount], [FakeAccount], [FakeAccount]
            unified = [[], [], [], []]

            # Sorting the adwords_id
            scores = defaultdict(int)
            for adwid in adwords_ids:
                if adwid in actives_0:
                    scores[adwid] += 3.1
                if adwid in actives_1:
                    scores[adwid] += 2
                if adwid in actives_2:
                    scores[adwid] += 1
            sorted_adwids = sorted(scores.iteritems(), key=lambda t: t[1], reverse=True)

            for adwid, score in sorted_adwids:
                unified[0].append(adwid)
                unified[1].append(actives_2[adwid])         # FakeAccount or None
                unified[2].append(actives_1[adwid])         # FakeAccount or None
                unified[3].append(actives_0[adwid])         # FakeAccount or None
            ret[user_id] = unified

        return sorted(ret.items(), key=lambda t: t[0])
