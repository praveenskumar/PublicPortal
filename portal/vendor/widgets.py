from collections import defaultdict

from portal.account.models import AccountStatusHelper as ASH
from portal.models import db
from portal.user import RolesEnum
from portal.user.models import User
from portal.utils.widgets import Widget
from portal.vendor.models import Vendor


class VendorStatistics(object):
    """Wrapper class for Vendor instances.
    """
    def __init__(self, vendor):
        self.vendor = vendor
        self.tally_status = defaultdict(int)

        self.count_activated = 0

        self.total_spent = 0
        self.max_spent = 0
        self.max_spent_account = None

    def __repr__(self):
        return ("<name:%(name)s "
                "total_spent:%(total_spent)s "
                "max_spent:%(max_spent)s "
                "count_activated:%(count_activated)s "
                ">") % dict(
                    name=self.vendor.name, total_spent=self.total_spent,
                    count_activated=self.count_activated, max_spent=self.max_spent)

    def compute(self):
        """Computes the following for accounts belonging to this vendor:
        - Sum of all spent_in_hkd
        - Tally of statuses
        - (Average, max) of spent_in_hkd:
        """
        for account in self.vendor.accounts:

            if not ASH.is_activated(account):
                continue

            self.count_activated += 1

            self.tally_status[account.status.name] += 1

            if account.spent_in_hkd:
                self.total_spent += account.spent_in_hkd
                if account.spent_in_hkd > self.max_spent:
                    self.max_spent = account.spent_in_hkd
                    self.max_spent_account = account


class VendorWidget(Widget):
    def get_roles(self):
        return [RolesEnum.ADMIN]

    def get_data(self):
        vendors = []
        for vendor in Vendor.query.order_by(Vendor.is_active.desc()):
            vs = VendorStatistics(vendor)
            vs.compute()
            vendors.append(vs)

        return vendors


class UserStatistics(object):
    """For each user:
    - How many accounts per provider
    - Sum of spending per provider
    - Average per provider
    """
    def __init__(self, user):
        self.user = user
        self.tally_count = defaultdict(int)
        self.tally_sum = defaultdict(float)

    def compute(self):
        for account in self.user.accounts:
            if not ASH.is_activated(account):
                continue
            if not account.vendor:
                continue

            self.tally_count[account.vendor] += 1
            if account.spent_in_hkd:
                self.tally_sum[account.vendor] += account.spent_in_hkd

    def __repr__(self):
        return unicode(self.user.id)


class VendorUserWidget(Widget):
    def get_roles(self):
        return [RolesEnum.ADMIN]

    def get_data(self):
        users = []
        for user in User.query.filter(User.id > 100):
            us = UserStatistics(user)
            us.compute()
            users.append(us)

        return users


class VendorMCCWidget(Widget):
    def get_roles(self):
        return [RolesEnum.ADMIN]

    def get_data(self):
        SQL = """
        SELECT DISTINCT C.company_name, B.login, B.status, B.actCount
        FROM
            accounts A
                INNER JOIN

            (SELECT login, status, COUNT(*) actCount
            FROM accounts
            GROUP BY login, status) B
                ON A.login = B.login
                INNER JOIN

            vendors C
                ON A.vendor_id = C.id

        ORDER BY C.company_name, B.login, B.status
        """
        results = defaultdict(lambda: defaultdict(list))
        for company_name, login, status, count in db.engine.execute(SQL):
            results[company_name][login].append((status, count))
        return results

