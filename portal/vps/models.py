
from collections import defaultdict

from flask import Markup

from portal.account.models import AccountStatus, association_table
from portal.models import TimeTrackedModel, db
from portal.vps import generate_key, generate_secret

DEAD = [AccountStatus.SUSPENDED, AccountStatus.ABANDONED]


class Vps(TimeTrackedModel):
    __tablename__ = 'vps'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(48), nullable=False)
    instance_id = db.Column(db.String(48))
    provider = db.Column(db.String(48), nullable=False)
    country = db.Column(db.String(48), nullable=False)
    ip_addr = db.Column(db.String(48))
    is_deleted = db.Column(db.Boolean(), default=False)
    login = db.Column(db.String(48), nullable=False)
    password = db.Column(db.String(48), nullable=False)

    api_key = db.Column(db.String(), default=generate_key)
    api_secret = db.Column(db.String(), default=generate_secret)

    accounts = db.relationship('Account',
                                                         secondary=association_table,
                                                         back_populates='VPSs')

    def __str__(self):
        return self.name

    @property
    def alive_count(self):
        bad = 0
        for account in self.accounts:
            if account.status in DEAD:
                bad += 1
        return len(self.accounts) - bad


    def _render_markup_list_view(self, is_alive):
        """Returns Markup for List View.
        """
        tele = defaultdict(int)
        for account in self.accounts:
            if is_alive and account.status not in DEAD:
                tele[account.status.value] += 1
            elif not is_alive and account.status in DEAD:
                tele[account.status.value] += 1

        ret = ""
        for status, count in tele.iteritems():
            ret += '<div>%s (%s)</div>' % (status, count)
        return Markup(ret)

    @property
    def alive_accounts(self):
        return self._render_markup_list_view(True)

    @property
    def dead_accounts(self):
        return self._render_markup_list_view(False)
