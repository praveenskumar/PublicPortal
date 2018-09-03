from flask import current_app
from portal.user import RolesEnum
from wtforms import StringField

from .utils import AuthorizationRequiredView, TimeTrackedModelView


class UserModelView(TimeTrackedModelView, AuthorizationRequiredView):
    can_view_details = True

    column_list = [ 'id', 'is_enabled', 'username', 'name', 'roles']
    column_editable_list = [ 'is_enabled' ]

    # https://stackoverflow.com/questions/39185230/flask-admin-overrides-password-when-user-model-is-changed
    form_excluded_columns = ('password')

    form_extra_fields = {
        'plain_password': StringField('Plain Password')
    }

    form_columns = ('id', 'is_enabled', 'username', 'name', 'plain_password', 'roles', 'budget_url')

    form_args = {
        'is_enabled': {},
        'username': {},
        'name': {},
        'plain_password': {},
        'roles': {},
        'budget_url': {
            'validators': [],     # validators.URL() is garbage
        }
    }

    column_details_exclude_list = ['password']

    def get_accessible_roles(self):
        return [RolesEnum.ADMIN.value]

    def on_model_change(self, form, user, is_created):
        if form.plain_password.data:        # Do not use `is not None` because it will turn to u''
            debug = form.plain_password.data
            print "PASSWORD DATA IS NOT NONE, CHANGING TO", debug, type(debug), len(debug)
            user.password = current_app.user_manager.hash_password(form.plain_password.data)


class RoleModelView(TimeTrackedModelView, AuthorizationRequiredView):
    def get_accessible_roles(self):
        return [RolesEnum.ADMIN.value]
