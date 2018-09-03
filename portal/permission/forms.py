
from flask_admin.form import BaseForm
from flask_babelex import gettext
from portal.permission.models import Permission


class PermissionCheckingAccountForm(BaseForm):
    """Performs Permission checking based on vendor and user.

    Requirements
    1. Existing accounts with (vendor_id, client_id) should not run into
    validation error if the modification is not related to either fields

    2. All new accounts should be subjected to checking.
    """

    def _get_error_msg(self, vendor, client):
        """Be careful, vendor or client can be None.
        """
        client_id = client.id if client else None
        vendor_id = vendor.id if vendor else None
        return gettext(
            'User(id=%(user_id)s) is not allowed to use accounts from Vendor(id=%(vendor_id)s).',
            user_id=client_id, vendor_id=vendor_id)

    def get_field_data_if_present(self, field_name):
        field = getattr(self, field_name, None)
        if field:
            return field.data

    def validate(self, *args, **kwargs):
        """This will be triggered when:
        1. We are creating/editing on Flask-Admin's forms
        2. Ajax updating through list-edtiable columns.

        For the case of #2, client/vendor will be missing.
        """
        if not super(PermissionCheckingAccountForm, self, *args, **kwargs).validate():
            return False

        if not self._obj:
            # If we are updating via ajax, both client and vendor will be empty.
            vendor = self.get_field_data_if_present('vendor')
            client = self.get_field_data_if_present('client')

            if client and vendor:
                if not Permission.check(vendor, client):
                    self.client.errors.append(self._get_error_msg(vendor, client))
                    return False
        else:
            vendor_or_user_modified = False

            vendor = self.get_field_data_if_present('vendor')
            client = self.get_field_data_if_present('client')

            if client and client != self._obj.client:
                vendor_or_user_modified = True
            if vendor and vendor != self._obj.vendor:
                vendor_or_user_modified = True

            if vendor_or_user_modified:
                if client is None:
                    client = self._obj.client
                if vendor is None:
                    vendor = self._obj.vendor

                if not Permission.check(vendor, client):
                    self.client.errors.append(self._get_error_msg(vendor, client))
                    return False

        return True

