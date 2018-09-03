
from collections import namedtuple

from flask import redirect, request, url_for
from flask_admin.base import expose
from flask_babelex import lazy_gettext as lg
from flask_babelex import gettext
from flask_user import current_user
from sqlalchemy import and_

from portal.admin.utils import AuthorizationRequiredView, TimeTrackedModelView
from portal.cache import cache, cache_helper
from portal.models import db
from portal.permission.models import Permission
from portal.user import RolesEnum
from portal.user.models import User, get_clients_query
from portal.utils import ColumnMetaContainer
from portal.vendor.models import Vendor

CMC = ColumnMetaContainer()
CMC.add(name='vendor', label=gettext('Vendor'))
CMC.add(name='user', label=gettext('User'))
CMC.add(name='notes', label=gettext('Notes'),
                description=lg('Why is this user allowed?'))


class PermissionModelView(TimeTrackedModelView, AuthorizationRequiredView):

    list_template = 'permission/list.html'

    page_size = 100

    def get_accessible_roles(self):
        return [RolesEnum.ADMIN.value]

    can_delete = True

    can_edit = True

    can_create = False

    column_descriptions = CMC.get_column_descriptions()

    form_args = CMC.get_form_args()

    form_excluded_columns = TimeTrackedModelView.form_excluded_columns + ['created_by']

    def get_html_id(self, vendor, user):
        return '%s_%s' % (vendor.id, user.id)

    @expose('/batch_update/vendor/<int:vendor_id>/', methods=['GET', 'POST'])
    def batch_update_by_vendor(self, vendor_id):
        """Convenient way to generate permissions en masse.
        """
        vendor = Vendor.query.get(vendor_id)
        users = get_clients_query()
        PermissionWrapper = namedtuple('PermissionWrapper', ['html_id', 'is_checked', 'notes'])

        if request.method == 'GET':
            permissions = []
            for user in users:
                p = Permission.query.filter(and_(Permission.vendor_id == vendor_id,
                                                                                 Permission.user_id == user.id)).one_or_none()
                permissions.append(PermissionWrapper(
                    html_id=self.get_html_id(vendor, user),
                    is_checked=bool(p),
                    notes=p.notes if p else None))

            return self.render('/permission/batch_update_by_vendor.html',
                                                 vendor=vendor,
                                                 permissions=permissions,
                                                 users=users)
        else:
            for user in users:
                html_id = self.get_html_id(vendor, user)
                checkbox_id = 'checkbox-' + html_id
                if checkbox_id in request.form:
                    notes_id = 'notes-' + html_id
                    self.upsert_if_necessary(vendor.id, user.id, request.form.get(notes_id))
                else:
                    self.delete_if_exists(vendor.id, user.id)
            return redirect(url_for('permission.index_view'))

    @expose('/batch_update/user/<int:user_id>/', methods=['GET', 'POST'])
    def batch_update_by_user(self, user_id):
        """Convenient way to generate permissions en masse.
        """
        user = User.query.get(user_id)
        vendors = Vendor.query.order_by(Vendor.id)
        PermissionWrapper = namedtuple('PermissionWrapper', ['html_id', 'is_checked', 'notes'])

        if request.method == 'GET':
            permissions = []
            for vendor in vendors:
                p = Permission.query.filter(and_(Permission.vendor_id == vendor.id,
                                                                                 Permission.user_id == user_id)).one_or_none()
                permissions.append(PermissionWrapper(
                    html_id=self.get_html_id(vendor, user),
                    is_checked=bool(p),
                    notes=p.notes if p else None))

            return self.render('/permission/batch_update_by_user.html',
                                                 vendors=vendors,
                                                 permissions=permissions,
                                                 user=user)
        else:
            for vendor in vendors:
                html_id = self.get_html_id(vendor, user)
                checkbox_id = 'checkbox-' + html_id
                if checkbox_id in request.form:
                    notes_id = 'notes-' + html_id
                    self.upsert_if_necessary(vendor.id, user.id, request.form.get(notes_id))
                else:
                    self.delete_if_exists(vendor.id, user.id)
            return redirect(url_for('permission.index_view'))

    def upsert_if_necessary(self, vendor_id, user_id, notes):
        p = Permission.query.filter(and_(Permission.vendor_id == vendor_id,
                                                                         Permission.user_id == user_id)).one_or_none()
        if p and p.notes != notes:
            p.notes = notes
            db.session.add(p)
            db.session.commit()
        elif not p:
            p = Permission()
            p.vendor_id = vendor_id
            p.user_id = user_id
            p.created_by_id = current_user.id
            if notes:
                p.notes = notes
            db.session.add(p)
            db.session.commit()

            key = cache_helper.get_clients_allowed_key(vendor_id)
            cache.delete(key)

    def delete_if_exists(self, vendor_id, user_id):
        conditions = and_(
                Permission.vendor_id == vendor_id,
                Permission.user_id == user_id)

        if Permission.query.filter(conditions).scalar() is not None:
            Permission.query.filter(conditions).delete()
            db.session.commit()

            key = cache_helper.get_clients_allowed_key(vendor_id)
            cache.delete(key)

    def on_model_change(self, form, model, is_created):
        model.created_by = current_user

    def on_model_delete(self, model):
        if model.vendor_id:
            key = cache_helper.get_clients_allowed_key(model.vendor_id)
            cache.delete(key)

    def render(self, template, **kwargs):
        if template == 'permission/list.html':
             kwargs['vendors'] = Vendor.query.filter(Vendor.is_active == True).order_by(Vendor.id)
             kwargs['users'] = get_clients_query().order_by(User.id)

        return super(PermissionModelView, self).render(template, **kwargs)

