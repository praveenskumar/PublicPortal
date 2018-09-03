from flask import Markup, url_for

from portal.account.models import Account
from portal.models import TimeTrackedModel, db
from portal.transfer.models import Transfer


class BankAccount(TimeTrackedModel):
    """Represents a Bank Account owned by a Vendor.
    """
    __tablename__ = 'bank_accounts'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String())
    details = db.Column(db.Text())

    vendors = db.relationship('Vendor', back_populates='bank_account')
    transfers = db.relationship('Transfer', back_populates='bank_account')

    def __str__(self):
        return self.name

    @property
    def transfer_count(self):
        url = url_for('transfer.index_view', flt1_0=self.name)
        count = Transfer.query.filter(Transfer.bank_account_id == self.id).count()
        return Markup('<u><a href=%s>%s</a></u>' % (url, count))

    @property
    def total_sent_in_hkd(self):
        total = 0
        for transfer in Transfer.query.filter(Transfer.bank_account_id == self.id):
            if transfer.net and transfer.exchange_rate:
                total += transfer.net * transfer.exchange_rate
        return total

    @property
    def total_spent_in_hkd(self):
        total = 0
        for act in Account.query.filter(Account.vendor_id.in_(
                [ v.id for v in self.vendors ])):
            total += act.spent_in_hkd
        return total

    @property
    def total_remaining_in_hkd(self):
        total = 0
        for act in Account.query.filter(Account.vendor_id.in_(
                [ v.id for v in self.vendors ])):
            if act.get_remaining_account_budget() and act.exchange_rate:
                total += act.get_remaining_account_budget() * act.exchange_rate
        return total

    @property
    def total_outstanding_in_hkd(self):
        return self.total_sent_in_hkd - self.total_spent_in_hkd - self.total_remaining_in_hkd

