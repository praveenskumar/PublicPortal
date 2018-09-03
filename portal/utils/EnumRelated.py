import sqlalchemy
from flask import json
from flask_admin._compat import iteritems, text_type
from flask_admin.babel import gettext
from flask_admin.contrib.sqla import ModelView, form
from flask_admin.contrib.sqla.form import AdminModelConverter
from flask_admin.form.fields import Select2Field
from flask_admin.model.form import converts
from flask_admin.model.widgets import XEditableWidget
from jinja2 import escape
from portal.account.models import AccountStatus, AccountStatusHelper
from wtforms.fields import HiddenField
from wtforms.fields.core import UnboundField
from wtforms.validators import InputRequired
from wtforms.widgets import HTMLString, html_params


class EnumField(Select2Field):
    """https://github.com/flask-admin/flask-admin/issues/1315
    """
    def __init__(self, column, **kwargs):
        assert isinstance(column.type, sqlalchemy.sql.sqltypes.Enum)

        def coercer(value):
            # coerce incoming value into an enum value
            if isinstance(value, column.type.enum_class):
                return value
            elif isinstance(value, basestring):
                return column.type.enum_class[value]
            else:
                assert False

        super(EnumField, self).__init__(
            choices=[(v, v) for v in column.type.enums],
            coerce=coercer,
            **kwargs)

    def pre_validate(self, form):
        # we need to override the default SelectField validation because it
        # apparently tries to directly compare the field value with the choice
        # key; it is not clear how that could ever work in cases where the
        # values and choice keys must be different types

        for (v, _) in self.choices:
            if self.data == self.coerce(v):
                break
        else:
            raise ValueError(self.gettext('Not a valid choice'))


class CustomAdminConverter(AdminModelConverter):
    @converts("sqlalchemy.sql.sqltypes.Enum")
    def conv_enum(self, field_args, **extra):
        return EnumField(column=extra["column"], **field_args)


class EnumEnabledXEditableWidget(XEditableWidget):
    def get_kwargs(self, field, kwargs):
        """See #MODIFICATION for more details.
        """
        if field.type == 'StringField':
            kwargs['data-type'] = 'text'
        elif field.type == 'TextAreaField':
            kwargs['data-type'] = 'textarea'
            kwargs['data-rows'] = '5'
        elif field.type == 'BooleanField':
            kwargs['data-type'] = 'select'
            # data-source = dropdown options
            kwargs['data-source'] = json.dumps([
                {'value': '', 'text': gettext('No')},
                {'value': '1', 'text': gettext('Yes')}
            ])
            kwargs['data-role'] = 'x-editable-boolean'
        elif field.type in ['Select2Field', 'SelectField']:
            kwargs['data-type'] = 'select'
            choices = [{'value': x, 'text': y} for x, y in field.choices]

            # prepend a blank field to choices if allow_blank = True
            if getattr(field, 'allow_blank', False):
                choices.insert(0, {'value': '__None', 'text': ''})

            # json.dumps fixes issue with unicode strings not loading correctly
            kwargs['data-source'] = json.dumps(choices)
        elif field.type == 'DateField':
            kwargs['data-type'] = 'combodate'
            kwargs['data-format'] = 'YYYY-MM-DD'
            kwargs['data-template'] = 'YYYY-MM-DD'
        elif field.type == 'DateTimeField':
            kwargs['data-type'] = 'combodate'
            kwargs['data-format'] = 'YYYY-MM-DD HH:mm:ss'
            kwargs['data-template'] = 'YYYY-MM-DD    HH:mm:ss'
            # x-editable-combodate uses 1 minute increments
            kwargs['data-role'] = 'x-editable-combodate'
        elif field.type == 'TimeField':
            kwargs['data-type'] = 'combodate'
            kwargs['data-format'] = 'HH:mm:ss'
            kwargs['data-template'] = 'HH:mm:ss'
            kwargs['data-role'] = 'x-editable-combodate'
        elif field.type == 'IntegerField':
            kwargs['data-type'] = 'text'
        elif field.type in ['FloatField', 'DecimalField']:
            kwargs['data-type'] = 'text'                # MODIFICATION: Bug with X-editable position
            kwargs['data-step'] = 'any'
        elif field.type in ['QuerySelectField', 'ModelSelectField',
                                                'QuerySelectMultipleField', 'KeyPropertyField',
                                                'EnumField' ]:        # MODIFICATION: Added new class for fieldtype

            # QuerySelectField and ModelSelectField are for relations
            kwargs['data-type'] = 'select'

            choices = []
            selected_ids = []
            for value, label, selected in field.iter_choices():
                try:
                    label = text_type(label)
                except TypeError:
                    # unable to display text value
                    label = ''

                choices.append({'value': text_type(value), 'text': label})
                if selected:
                    selected_ids.append(value)

            self.set_choices(kwargs, choices)

            if field.type == 'QuerySelectMultipleField':
                kwargs['data-type'] = 'select2'
                kwargs['data-role'] = 'x-editable-select2-multiple'

                # must use id instead of text or prefilled values won't work
                separator = getattr(field, 'separator', ',')
                kwargs['data-value'] = separator.join(selected_ids)
        else:
            raise Exception('Unsupported field type: %s' % (type(field),))

        return kwargs

    def set_choices(self, keywordargs, choices):
        """Substitues long repetitive data-sources

        We will pass replacement_bank to the widget as kwargs if the field name
        is in one of ReplacementBank.field_name.
        """
        replacement_bank = keywordargs.get('replacement_bank', None)
        if replacement_bank:
            keywordargs.pop('replacement_bank')
            replacement_id = replacement_bank.get_replacement_id(json.dumps(choices))
            keywordargs['data-replacement_id'] = replacement_id
        else:
            keywordargs['data-source'] = json.dumps(choices)


class StatusEnumEnabledXEditableWidget(EnumEnabledXEditableWidget):
    """EnumEnabledXEditableWidget for the 'status' field which requires translation.

    1. text rendered in html will be in the format of English_Chinese.
    2. html_node will have data-source=[{ value: ENGLISH, text: English_Chinese }, ..]
    """
    def __call__(self, field, **kwargs):
        kwargs.setdefault('data-value', kwargs.pop('display_value', ''))

        kwargs.setdefault('data-role', 'x-editable')
        kwargs.setdefault('data-url', './ajax/update/')

        kwargs.setdefault('id', field.id)
        kwargs.setdefault('name', field.name)
        kwargs.setdefault('href', '#')

        if not kwargs.get('pk'):
            raise Exception('pk required')
        kwargs['data-pk'] = str(kwargs.pop("pk"))

        kwargs['data-csrf'] = kwargs.pop("csrf", "")

        kwargs = self.get_kwargs(field, kwargs)

        return HTMLString(
            '<a %s>%s</a>' % (html_params(**kwargs),
                                         escape(kwargs['data-display-text']))
        )

    def get_kwargs(self, field, kwargs):
        """Setting data-display-text and data-value manually.
        """
        assert field.name == 'status', \
                "A field other than 'status' is using the StatusEnumEnabledXEditableWidget"

        kwargs['data-type'] = 'select'

        choices = []
        for value, label, selected in field.iter_choices():
            try:
                label = text_type(label)
            except TypeError:
                # unable to display text value
                label = ''

            status_enum = getattr(AccountStatus, text_type(label))
            l = AccountStatusHelper.translate(status_enum)
            choices.append({'value': text_type(value), 'text': l})

            if selected:
                kwargs['data-display-text'] = l
                kwargs['data-value'] = text_type(value)

        self.set_choices(kwargs, choices)

        return kwargs


def enum_create_editable_list_form(form_base_class, form_class, widget=None):
    if widget is None:
        widget = EnumEnabledXEditableWidget()            # Modification

    class ListForm(form_base_class):
        list_form_pk = HiddenField(validators=[InputRequired()])

    # iterate FormMeta to get unbound fields, replace widget, copy to ListForm
    for name, obj in iteritems(form_class.__dict__):

        if isinstance(obj, UnboundField):
            if name == 'status':                            # Modification
                obj.kwargs['widget'] = StatusEnumEnabledXEditableWidget()
            else:
                obj.kwargs['widget'] = widget
            setattr(ListForm, name, obj)

            if name == "list_form_pk":
                raise Exception('Form already has a list_form_pk column.')

    return ListForm


class EnumSQLAModelView(ModelView):

    model_form_converter = CustomAdminConverter

    def scaffold_list_form(self, widget=None, validators=None):
        converter = self.model_form_converter(self.session, self)
        form_class = form.get_form(self.model, converter,
                                     base_class=self.form_base_class,
                                     only=self.column_editable_list,
                                     field_args=validators)

        # Modification
        return enum_create_editable_list_form(self.form_base_class, form_class,
                                         widget)
