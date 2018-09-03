
from flask import current_app
from flask_user import UserMixin
from sqlalchemy import and_

from portal.models import TimeTrackedModel, db
from portal.user import RolesEnum


class User(TimeTrackedModel, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    username = db.Column(db.String(255), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    is_enabled = db.Column(db.Boolean(), nullable=False, default=False)

    roles = db.relationship('Role', secondary='users_roles',
                                                 backref=db.backref('users', lazy='dynamic'))

    accounts = db.relationship('Account', back_populates='client')
    permissions = db.relationship('Permission', foreign_keys='Permission.user_id', back_populates='user')

    accesses = db.relationship('Access', back_populates='user')

    budget_url = db.Column(db.String(1024))

    def is_active(self):
        return self.is_enabled

    def __str__(self):
        return self.username


class Role(TimeTrackedModel):
    __tablename__ = 'roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)    # for @roles_accepted()

    def __str__(self):
        return self.name


class UsersRoles(TimeTrackedModel):
    __tablename__ = 'users_roles'
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id', onupdate='cascade', ondelete='cascade'))
    role_id = db.Column(db.Integer(), db.ForeignKey('roles.id', ondelete='cascade'))


def find_or_create_role(name):
    role = Role.query.filter(Role.name == name).first()
    if not role:
        role = Role(name=name)
        db.session.add(role)
    return role


def find_or_create_user(username, password, name):
    user = User.query.filter(User.username == username).first()
    if not user:
        user = User()
        user.username=username
        user.password=current_app.user_manager.hash_password(password)
        user.name=name
        user.is_enabled=True
        db.session.add(user)
    return user


def get_clients_query():
    return User.query.join(UsersRoles).join(Role).filter(
        and_(User.id == UsersRoles.user_id,
                 User.is_enabled == True,
                 UsersRoles.role_id == Role.id,
                 Role.name == RolesEnum.CLIENT.value))
