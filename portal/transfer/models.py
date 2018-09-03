
from flask import Markup

from portal.models import TimeTrackedModel, db


class Transfer(TimeTrackedModel):
    """
    Represents a transfer of money TO or FROM a Bank Account.

    Transferring TO:
        - payment to vendors
        - counter_party becomes "origin"

    Transferring FROM:
        - refund from vendors
        - counter_party becomes "destination"
    """
    __tablename__ = 'transfers'

    id = db.Column(db.Integer, primary_key=True)

    bank_account_id = db.Column(db.Integer(), db.ForeignKey('bank_accounts.id', onupdate="cascade"))
    bank_account = db.relationship('BankAccount', back_populates='transfers')

    counter_party = db.Column(db.String(96))

    gross = db.Column(db.Float(), nullable=False)
    net = db.Column(db.Float())
    currency = db.Column(db.String(12))
    exchange_rate = db.Column(db.Float(), nullable=False)

    is_refund = db.Column(db.Boolean, default=False)

    notes = db.Column(db.Text())
    date = db.Column(db.Date(), nullable=False)

    @property
    def suggested_net(self):
        pcts = set()
        for vendor in self.bank_account.vendors:
            pcts.add(vendor.service_fee)

        if not pcts:
            return "Not Set"

        pcts = sorted(list(pcts))

        ret = Markup('<ul>')
        for pct in pcts:
            ret += Markup('<li>')
            amt = self.gross * (100-pct) / 100.0
            ret += '%.2f (%s%%)' % (amt, pct)
            ret += Markup('</li>')
        ret += Markup('</ul>')

        return ret

