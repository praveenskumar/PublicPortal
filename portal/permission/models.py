
from portal.models import TimeTrackedModel, db
from sqlalchemy import and_


class Permission(TimeTrackedModel):
    __tablename__ = 'permissions'

    __table_args__ = (db.UniqueConstraint('vendor_id', 'user_id', name='permission_vendor_user'), )

    id = db.Column(db.Integer, primary_key=True)

    vendor_id = db.Column(db.Integer(), db.ForeignKey('vendors.id', onupdate="cascade"), nullable=False)
    vendor = db.relationship('Vendor', back_populates='permissions')

    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', onupdate="cascade"), nullable=False)
    user = db.relationship('User', foreign_keys=[user_id], back_populates='permissions')

    created_by_id = db.Column(db.Integer(), db.ForeignKey('users.id', onupdate="cascade"))
    created_by = db.relationship('User', foreign_keys=[created_by_id])

    notes = db.Column(db.Text())

    def __str__(self):
        return '%s - %s' % (self.vendor, self.user)

    @classmethod
    def check(self, vendor, user):
        """https://stackoverflow.com/questions/32938475/flask-sqlalchemy-check-if-row-exists-in-table
        """
        if vendor and user:
            return db.session.query(db.exists().where(
                and_(Permission.vendor_id == vendor.id, Permission.user_id == user.id))).scalar()

