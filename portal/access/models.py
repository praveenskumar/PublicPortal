
from portal.models import db
from sqlalchemy.sql import func


class Access(db.Model):
    __tablename__ = 'accesses'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', onupdate="cascade"), nullable=False)
    user = db.relationship('User', back_populates='accesses')

    account_id = db.Column(db.Integer(), db.ForeignKey('accounts.id', onupdate="cascade"), nullable=False)
    account = db.relationship('Account', back_populates='accesses')

    def __init__(self, user_id=None, account_id=None):
        self.user_id = user_id
        self.account_id = account_id
