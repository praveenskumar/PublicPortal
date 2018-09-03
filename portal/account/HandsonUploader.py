import json

from flask import jsonify, request
from flask_admin import expose
from flask_admin.contrib.sqla import ModelView
from flask_babelex import lazy_gettext
from portal.account.models import AccountStatusHelper
from portal.models import db
from werkzeug.datastructures import MultiDict


def encode_utf8(obj):
    return unicode(obj).encode('utf-8')


class HandsonUploader(ModelView):

    # it's very difficult to make this class abstract
    excluded_columns = ['nickname', 'auto_tag_on', 'daily_budget', 'external_comment',
                        'account_budget_override', 'remaining_account_budget_override']

    @expose('/handson_batch/')
    def batch_upload(self):
        """Renders the base template for this page.
        """
        return self.render('account/handson_batch.html')

    @expose('/handson_batch/setup_data')
    def return_setup_data(self):
        """Returns all the data needed to setup handson-table.
        """
        columns = self.get_wtfields()
        response_raw = {
            'column_names': self.get_column_header_labels(columns),
            'column_properties': self.get_column_properties(columns),
        }
        return jsonify(response_raw)

    def get_column_header_labels(self, fields):
        ret = []
        for field in fields:
            label = lazy_gettext(field.label.text)
            if field.flags.required:
                label = label + ' *'
            ret.append(label)
        return ret

    def get_wtfields(self):
        """Returns WTForm Columns.
        """
        columns = []
        for col in self.create_form():
            if self.form_excluded_columns and col.name in self.form_excluded_columns:
                continue

            if col.name in self.excluded_columns:
                continue

            # if form_columns is not defined, add by default
            # if defined need to verify that it's part of it
            if not self.form_columns or col.name in self.form_columns:
                columns.append(col)

        return columns

    def get_column_properties(self, wtfields):
        """Builds a list of properties for each columns in wtcolumsn.
        """
        ret = []
        for field in wtfields:
            name = field.name
            prop = {}

            if name == 'adwords_id':
                # let WTForm handle the validation
                prop['allowEmpty'] = False
            elif name == 'status':
                prop['type'] = 'dropdown'
                prop['source'] = [label for value, label, description in
                                  AccountStatusHelper.iternew()]
            elif name == 'is_unlimited':
                prop['type'] = 'checkbox'
            elif name == 'currency':
                prop['type'] = 'dropdown'
                prop['source'] = ['USD', 'HKD', 'RMB', 'SGD', 'VND', 'NTD', 'JPY', 'MYR', 'AUD',
                                  'EUR', 'ARS']
            elif name in ['account_budget', 'remaining_account_budget', 'exchange_rate']:
                prop['type'] = 'numeric'
                prop['numericFormat'] = {'pattern': '0,0.00', 'culture': 'en-US'}

            if field.type == 'EnumField':
                pass        # noop - Check for "status" explicitly instead.
            elif field.type in ['QuerySelectField', 'QuerySelectMultipleField']:
                prop['type'] = 'dropdown'
                c = []
                for value, obj, checked in field.iter_choices():
                    if value != '__None':
                        c.append(encode_utf8(obj))
                prop['source'] = c

            ret.append(prop)
        return ret

    def is_empty(self, row):
        return not any(row)

    def map_row_to_dict(self, row):
        """Maps raw data from JS (handson-table) to data compatible to WTForm.

        For each WTForm field, these are the label and values from self.get_create_form()
            FIELD, VALUE, LABEL
            client __None
            client 121 alex121
            vendor __None
            vendor 8 AsiaPac Net Media Limited
            vps __None
            vps 49 HK-031

        LABEL is rendered in JS handson table. To achieve what we want,
        we need to map these labels back to values.
        """
        fields = self.get_wtfields()
        assert len(fields) == len(row), "JS Table columns does not match WTForm's."

        data = MultiDict()
        for i, raw_value in enumerate(row):
            if raw_value is None:
                continue

            field = fields[i]

            if field.name == 'status':
                try:
                    # get_value takes unicode only
                    data['status'] = AccountStatusHelper.get_value(raw_value)
                except KeyError:
                    if raw_value:
                        raise ValueError("Bad value supplied to 'status': %s" % raw_value)
                    else:
                        pass            # no status given, hand off to sqlalchemy for default

            elif field.type in ['QuerySelectField', 'QuerySelectMultipleField']:
                reverse_map = {}
                for value, obj, checked in field.iter_choices():
                    # When we rendered the form, we mapped an object to a string.    Now,
                    # we will map the object to a string and then associate it with a
                    # value which we will be assigning to the wtform later
                    label = encode_utf8(obj)
                    reverse_map[label] = value
                try:
                    data[field.name] = reverse_map[encode_utf8(raw_value)]
                except KeyError:
                    # NOTE: we cannot attach this error to the wtform right here because
                    # wtform.field.errors can only be appended after you have binded data
                    # to it. Since we need this method to execute to get the data needed
                    # for binding, we will just assign a bad value to wtform which will
                    # drop the value altogether and report as value missing.
                    pass
            else:
                data[field.name] = encode_utf8(raw_value)

        return data

    @expose('/handson_batch/submit', methods=['POST'])
    def submit(self):
        """Parses the submission from pressing the submit button

        - Returns errors from validations.
        - Creation will only happen if validation passes for ALL rows.
        """
        good_forms = []

        # {row_num: {label: [ error_msg, .. ]}
        errors = {}

        for row_num, row in enumerate(json.loads(request.form['rows'])):
            if self.is_empty(row):
                continue

            form = self.get_create_form()
            data = self.map_row_to_dict(row)
            form = form(data)
            if form.validate():
                good_forms.append(form)
            else:
                # Map the field_name to label for translation purposes
                new_errors = []
                for field_name, messages in form.errors.iteritems():
                    translated_label = lazy_gettext(getattr(form, field_name).label.text)
                    new_errors.append((translated_label, messages))
                errors[row_num + 1] = new_errors

        # If we have any errors, do not proceed with creation and saving
        if errors:
            return jsonify({'success': False, 'errors': errors, 'accounts_added': 0})

        for form in good_forms:
            model = self.model()
            form.populate_obj(model)
            db.session.add(model)         # TODO remove db reference to DRY
            self._on_model_change(form, model, True)
            # NOTE .commit has been moved here (inside the loop) due to
            # unique nature of transaction_id for account_vps_version
            db.session.commit()

        return jsonify({'success': True, 'accounts_added': len(good_forms)})
