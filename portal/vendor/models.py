
from portal.account.models import Account, AccountStatusHelper
from portal.models import TimeTrackedModel, db
from sqlalchemy import and_
from sqlalchemy.sql import expression


class Vendor(TimeTrackedModel):
    __tablename__ = 'vendors'

    id = db.Column(db.Integer, primary_key=True)

    nickname = db.Column(db.String(48), unique=True)
    company_name = db.Column(db.String(48), nullable=False)
    contact_name = db.Column(db.String(48), nullable=False)

    payments_account_id = db.Column(db.String(30))
    payments_profile_id = db.Column(db.String(30), unique=True)
    notes = db.Column(db.Text())

    count_total = db.Column(db.Integer)
    count_bad = db.Column(db.Integer)

    bank_account_id = db.Column(db.Integer(), db.ForeignKey('bank_accounts.id', onupdate="cascade"))
    bank_account = db.relationship('BankAccount', back_populates='vendors')

    accounts = db.relationship('Account', back_populates='vendor')
    permissions = db.relationship('Permission', back_populates='vendor')

    is_active = db.Column(db.Boolean(), server_default=expression.true(), default=True)

    days_to_topup = db.Column(db.Integer)
    service_fee = db.Column(db.Float())

    def __str__(self):
        if self.payments_profile_id:
            return self.payments_profile_id[:4] + ' ' + self.company_name
        return self.company_name

    @property
    def num_accounts_total(self):
        return len(self.accounts)

    @property
    def num_accounts_unused(self):
        return db.session.query(Account).filter(and_(
            Account.vendor_id == self.id,
            Account.status.in_(AccountStatusHelper.unactivated_statuses)
        )).count()

    @property
    def num_accounts_used(self):
        return self.num_accounts_total - self.num_accounts_unused

    @property
    def total_spent_in_hkd(self):
        total = 0
        for act in Account.query.filter(Account.vendor_id == self.id):
            total += act.spent_in_hkd
        return total

    @property
    def has_bank_account(self):
        return bool(self.bank_account)
