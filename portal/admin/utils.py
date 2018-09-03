from datetime import datetime

import pytz
from flask import (Blueprint, Response, current_app, redirect, render_template,
                                     request, url_for)
from flask_admin.base import BaseView, expose
from flask_admin.model import typefmt
from flask_user import current_user
from flask_user.access import is_authenticated
from portal.utils.EnumRelated import EnumSQLAModelView


class TimeTrackedModelView(EnumSQLAModelView):
    column_default_sort = ('updated_at', True)
    column_exclude_list = [ 'created_at' ]
    can_delete = False

    form_excluded_columns = [ 'created_at', 'updated_at' ]

    def date_format(view, value):
        """Now dt is stored as tz.tzlocal which is +00.
        """
        value = value.astimezone(pytz.timezone('Asia/Hong_Kong'))
        return value.strftime('%m/%d %H:%M %Z')

    MY_DEFAULT_FORMATTERS = dict(typefmt.BASE_FORMATTERS)
    MY_DEFAULT_FORMATTERS.update({
        datetime: date_format
    })
    column_type_formatters = MY_DEFAULT_FORMATTERS


class AuthorizationRequiredView(BaseView):

    def get_accessible_roles(self):
        raise NotImplemented("Override AuthorizationRequiredView.get_accessible_roles not set.")

    def is_accessible(self):
        if not is_authenticated():
            return False
        if not current_user.has_role(*self.get_accessible_roles()):
            return False
        return True

    def inaccessible_callback(self, name, **kwargs):
        if not is_authenticated():
            return current_app.user_manager.unauthenticated_view_function()
        if not current_user.has_role(*self.get_accessible_roles()):
            return current_app.user_manager.unauthorized_view_function()


class AccessControlView(EnumSQLAModelView):
    """For most cases, we will delegate most of the checking to the super method.
    """

    # Override this if you want to use an attribute other than user_id for ACL
    access_attribute = 'user_id'

    def get_query(self):
        """Jails the user to only see their models.
        """
        base = super(AccessControlView, self).get_query()
        return base.filter(getattr(self.model, self.access_attribute) == current_user.id)

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        model_id = request.args.get('id', None)
        if model_id:        # If not, let super handle
            model = self.get_one(model_id)
            if model and getattr(model, self.access_attribute) != current_user.id:
                return current_app.user_manager.unauthorized_view_function()
        return super(AccessControlView, self).edit_view()

    @expose('/details/', methods=('GET', 'POST'))
    def details_view(self):
        model_id = request.args.get('id', None)
        if model_id:        # If not, let super handle
            model = self.get_one(model_id)
            if model and getattr(model, self.access_attribute) != current_user.id:
                return current_app.user_manager.unauthorized_view_function()
        return super(AccessControlView, self).details_view()

    @expose('/delete/', methods=('POST',))
    def delete_view(self):
        form = self.delete_form()
        if self.validate_form(form):
            model_id = form.id.data
            model = self.get_one(model_id)
            if getattr(model, self.access_attribute) != current_user.id:
                return current_app.user_manager.unauthorized_view_function()
        return super(AccessControlView, self).delete_view()
