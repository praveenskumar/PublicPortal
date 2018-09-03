import unittest
from collections import namedtuple

from flask import current_app, url_for
from flask_login import current_user, login_user
from flask_user import signals
from flask_user.views import _do_login_user, logout_user
from portal.account.models import AttributeManagerSingleton as AMS
from portal.account.models import Account
from portal.config import Core
from portal.factory import create_app
from portal.models import db
from portal.permission.models import Permission
from portal.user import RolesEnum
from portal.user.models import find_or_create_role, find_or_create_user
from portal.vendor.models import Vendor


class CustomConfig(Core):
    SQLALCHEMY_DATABASE_URI = 'postgresql://localhost/portal_testing'
    TESTING = True
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = False
    MAIL_SUPPRESS_SEND = True
    SERVER_NAME = 'localhost'


UserData = namedtuple('UserData', ['username', 'password', 'name'])
ud_admin = UserData(username='admin', password='admin', name='admin')
ud_support = UserData(username='support', password='support', name='support')
ud_technician = UserData(username='technician', password='technician', name='technician')
ud_client1 = UserData(username='client1', password='client1', name='client1')
ud_client2 = UserData(username='client2', password='client2', name='client2')

AccountData = namedtuple('AccountData', ['adwords_id', 'nickname'])
ad_1 = AccountData(adwords_id='123-456-9991', nickname='nickname_1')
ad_2 = AccountData(adwords_id='223-456-9992', nickname='nickname_2')


class AccountViewsTest(unittest.TestCase):

    def setUp(self):
        self.app = create_app(CustomConfig)
        self.app_context = self.app.app_context()
        self.client = self.app.test_client()
        self.db = db

        self.app_context.push()
        self.db.create_all()
        self._fixtures()

    def tearDown(self):
        self.db.session.remove()
        self.db.drop_all()
        self.app_context.pop()

    def _fixtures(self):
        admin_role = find_or_create_role(RolesEnum.ADMIN.value)
        support_role = find_or_create_role(RolesEnum.SUPPORT.value)
        technician_role = find_or_create_role(RolesEnum.TECHNICIAN.value)
        client_role = find_or_create_role(RolesEnum.CLIENT.value)

        self.admin = find_or_create_user(ud_admin.username, ud_admin.password, ud_admin.name)
        self.support = find_or_create_user(ud_support.username, ud_support.password, ud_support.name)
        self.technician = find_or_create_user(ud_technician.username, ud_technician.password, ud_technician.name)
        self.client1 = find_or_create_user(ud_client1.username, ud_client1.password, ud_client1.name)
        self.client2 = find_or_create_user(ud_client2.username, ud_client2.password, ud_client2.name)

        self.admin.roles.append(admin_role)
        self.support.roles.append(support_role)
        self.technician.roles.append(technician_role)
        self.client1.roles.append(client_role)
        self.client2.roles.append(client_role)

        def _create_account(account_data):
            a = Account()
            a.adwords_id = account_data.adwords_id
            a.nickname = account_data.nickname
            db.session.add(a)
            return a

        self.account_1 = _create_account(ad_1)
        self.account_2 = _create_account(ad_2)
        self.client1.accounts.append(self.account_1)
        self.client2.accounts.append(self.account_2)
        self.db.session.commit()

    def login(self, ud):
        """Why do we have to user UserData as opposed to User?
        !!!
        If you login with a User instance, the password is HASHED. This results in a
        mysterious page where there are no flash messages whatsoever.
        !!!
        """
        assert type(ud) is UserData
        r = self.client.post(url_for('user.login'),
                                                 data=dict(username=ud.username, password=ud.password),
                                                 follow_redirects=True)
        assert 'You have signed in successfully' in r.data

    def logout(self):
        """TODO change base template for logout page to include flash
        """
        r = self.client.post(url_for('user.logout'), follow_redirects=True)
        #assert 'You have successfully logged out' in r.data


class ACLRoleTest(AccountViewsTest):
    """Tests what each role can and cannot do.
    """
    def test_access_per_role(self):
        """Test which views are allowed for each role.
        """
        self.login(ud_admin)
        r = self.client.get(url_for('admin_account.index_view'), follow_redirects=True)
        assert ad_1.adwords_id in r.data
        r = self.client.get(url_for('support_account.index_view'), follow_redirects=True)
        assert ad_1.adwords_id in r.data
        r = self.client.get(url_for('technician_account.index_view'), follow_redirects=True)
        assert ad_1.adwords_id in r.data
        r = self.client.get(url_for('client_account.index_view'), follow_redirects=True)
        assert 'There are no items in the table.' in r.data             # client_account locks down to current_user
        self.logout()

        self.login(ud_technician)
        r = self.client.get(url_for('admin_account.index_view'), follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        r = self.client.get(url_for('support_account.index_view'), follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        r = self.client.get(url_for('technician_account.index_view'), follow_redirects=True)
        assert ad_1.adwords_id in r.data
        r = self.client.get(url_for('client_account.index_view'), follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        self.logout()

        self.login(ud_support)
        r = self.client.get(url_for('admin_account.index_view'), follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        r = self.client.get(url_for('support_account.index_view'), follow_redirects=True)
        assert ad_1.adwords_id in r.data
        r = self.client.get(url_for('technician_account.index_view'), follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        r = self.client.get(url_for('client_account.index_view'), follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        self.logout()

        self.login(ud_client1)
        r = self.client.get(url_for('admin_account.index_view'), follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        r = self.client.get(url_for('support_account.index_view'), follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        r = self.client.get(url_for('technician_account.index_view'), follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        r = self.client.get(url_for('client_account.index_view'), follow_redirects=True)
        assert ad_1.adwords_id in r.data
        self.logout()

    def test_client_actions_on_his_data(self):
        """Tests a client's permissions to access his data.
        """
        self.login(ud_client1)
        r = self.client.get(url_for('client_account.index_view'))
        assert ad_1.nickname in r.data
        assert ad_2.nickname not in r.data
        r = self.client.get(url_for('client_account.edit_view', id=self.account_1.id),
                                                follow_redirects=True)
        assert ad_1.nickname in r.data
        r = self.client.get(url_for('client_account.details_view', id=self.account_1.id),
                                                follow_redirects=True)
        assert ad_1.nickname in r.data
        # Since deletion is not allowed, we will be redirected to index_view with
        # the record still present
        r = self.client.post(url_for('client_account.delete_view', id=self.account_1.id),
                                                 follow_redirects=True)
        assert ad_1.nickname in r.data

    def test_client_actions_on_others_data(self):
        """Tests a client's inability to modify other client's data.
        """
        self.login(ud_client1)
        r = self.client.get(url_for('client_account.edit_view', id=self.account_2.id),
                                                follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        r = self.client.get(url_for('client_account.details_view', id=self.account_2.id),
                                                follow_redirects=True)
        assert 'You do not have permission to access' in r.data
        # Since deletion is not allowed, we will be redirected to index_view with
        # the record still present
        r = self.client.post(url_for('client_account.delete_view', id=self.account_2.id),
                                                 follow_redirects=True)
        assert 'You do not have permission to access' in r.data



class DataVisibilityTest(AccountViewsTest):
    """Tests what data each role can and cannot see.
    """
    def _test_index_view(self, role, user_data):
        READ_COLUMNS = set([ c.name for c in Account.__table__.columns])
        READ_COLUMNS = READ_COLUMNS - set(['id'])

        role_columns = set(AMS.get_list_view_columns(role))

        self.login(user_data)
        r = self.client.get(url_for('%s_account.index_view' % role))

        # Can't just look for col-X right now because of CSS sheets.
        for column in role_columns:
            assert 'column-header col-' + column in r.data
        for column in READ_COLUMNS - role_columns:
            assert 'column-header col-' + column not in r.data
        self.logout()

    def test_readable(self):
        """Since column_list and column_details_list reference the same list, we do
        not need to test details_list separately
        """
        self._test_index_view(RolesEnum.ADMIN.value, ud_admin)
        self._test_index_view(RolesEnum.TECHNICIAN.value, ud_technician)
        self._test_index_view(RolesEnum.SUPPORT.value, ud_support)
        self._test_index_view(RolesEnum.CLIENT.value, ud_client1)

    def _test_edit_view(self, role, user_data, account):
        EDIT_COLUMNS = set([ c.name for c in Account.__table__.columns])
        EDIT_COLUMNS = EDIT_COLUMNS - set(['id', 'vps_id', 'client_id', 'vendor_id'])
        EDIT_COLUMNS.update(['vps', 'client', 'vendor'])

        if AMS.get_all_editable_columns(role) is None:
            role_columns = EDIT_COLUMNS         # For Admin which has this set to None
        else:
            role_columns = set(AMS.get_all_editable_columns(role))

        self.login(user_data)
        r = self.client.get(url_for('%s_account.edit_view' % role, id=account.id))
        for column in role_columns:
            assert 'for="' + column in r.data, column
        for column in EDIT_COLUMNS - role_columns:
            assert 'for="' + column not in r.data, column
        self.logout()

    def test_editable(self):
        self._test_edit_view(RolesEnum.ADMIN.value, ud_admin, self.account_1)
        self._test_edit_view(RolesEnum.TECHNICIAN.value, ud_technician, self.account_1)
        self._test_edit_view(RolesEnum.SUPPORT.value, ud_support, self.account_1)
        self._test_edit_view(RolesEnum.CLIENT.value, ud_client1, self.account_1)


class VendorUserPermissionTest(AccountViewsTest):

    def setUp(self):
        super(VendorUserPermissionTest, self).setUp()
        self.vendor = Vendor()
        self.vendor.company_name = 'company_name_1'
        self.vendor.contact_name = 'contact_name_1'
        db.session.add(self.vendor)
        db.session.commit()

        # Account_1 is tied to vendor_1
        self.account_1.vendor = self.vendor
        db.session.add(self.account_1)
        db.session.commit()

        self.login(ud_admin)            # Login for admin for all tests
        self.post_data = dict(adwords_id=ad_1.adwords_id,
                                                    status='ABANDONED',
                                                    login='login_1',
                                                    password='password_1')

    def test_client_vendor_not_modified_passing(self):
        """Even though no permission exist for (vendor, client), not setting
        client/vendor does not trigger validation error.
        """
        rv = self.client.post(url_for('admin_account.edit_view', id=self.account_1.id),
                                                    data=self.post_data, follow_redirects=True)
        assert 'Record was successfully saved.' in rv.data

    def test_client_vendor_set_failing(self):
        """Permission for client_id, vendor_id not set results in fail.
        """
        self.post_data['client'] = self.client2.id
        rv = self.client.post(url_for('admin_account.edit_view', id=self.account_1.id),
                                                    data=self.post_data, follow_redirects=True)
        assert 'is not allowed to use accounts from Vendor' in rv.data

    def test_permission_enabled_test_ok(self):
        """Permission enabled, should pass now.
        """
        p = Permission()
        p.user_id = self.client2.id
        p.vendor_id = self.vendor.id
        db.session.add(p)
        db.session.commit()

        self.post_data['client'] = self.client2.id
        rv = self.client.post(url_for('admin_account.edit_view', id=self.account_1.id),
                                                    data=self.post_data, follow_redirects=True)
        assert 'Record was successfully saved.' in rv.data

    def test_legacy_data_not_affected(self):
        self.account_1.user_id = self.client1.id
        db.session.add(self.account_1)
        db.session.commit()

        # Not updating vendor nor client, passing
        rv = self.client.post(url_for('admin_account.edit_view', id=self.account_1.id),
                                                    data=self.post_data, follow_redirects=True)
        assert 'Record was successfully saved.' in rv.data

        self.post_data['client'] = self.client2.id
        rv = self.client.post(url_for('admin_account.edit_view', id=self.account_1.id),
                                                    data=self.post_data, follow_redirects=True)
        assert 'is not allowed to use accounts from Vendor' in rv.data

    def skip_test_vendor_not_set(self):
        """Vendor is required by now. This test is deprecated.
        """
        self.account_1.vendor = None
        db.session.add(self.account_1)
        db.session.commit()
        assert Account.query.get(self.account_1.id).vendor is None

        rv = self.client.post(url_for('admin_account.edit_view', id=self.account_1.id),
                                                    data=self.post_data, follow_redirects=True)
        assert 'This field is required.' in rv.data

        # TODO figure out this edge case
        self.post_data['client'] = self.client2.id
        rv = self.client.post(url_for('support_account.edit_view', id=self.account_1.id),
                                                    data=self.post_data, follow_redirects=True)
        assert "Failed to update record." in rv.data

    def test_non_admin_passing(self):
        # Not updating vendor nor client, passing
        rv = self.client.post(url_for('technician_account.edit_view', id=self.account_1.id),
                                                    data=self.post_data, follow_redirects=True)
        assert 'Record was successfully saved.' in rv.data

        self.post_data['client'] = self.client2.id
        rv = self.client.post(url_for('technician_account.edit_view', id=self.account_1.id),
                                                    data=self.post_data, follow_redirects=True)
        assert 'is not allowed to use accounts from Vendor' in rv.data

        p = Permission()
        p.user_id = self.client2.id
        p.vendor_id = self.vendor.id
        db.session.add(p)
        db.session.commit()

        self.post_data['client'] = self.client2.id
        rv = self.client.post(url_for('technician_account.edit_view', id=self.account_1.id),
                                                    data=self.post_data, follow_redirects=True)
        assert 'Record was successfully saved.' in rv.data




if __name__ == "__main__":
    unittest.main()
