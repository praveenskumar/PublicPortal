import itertools
from collections import OrderedDict, defaultdict, namedtuple

ColumnMeta = namedtuple('ColumMeta', ['name', 'label', 'description'])


class ColumnMetaContainer(object):

    def __init__(self):
        self.bank = []

    def get_form_args(self):
        """Returns FlaskAdmin parameters related to labels used in create/edit forms.
        {
            name: {
                'label': label,
                'description': description,
            },
        }
        """
        ret = {}
        for cm in self.bank:
            u = dict(label=cm.label)
            if cm.description:
                u.update({'description': cm.description})
            ret[cm.name] = u

        return ret

    def get_column_descriptions(self):
        """Returns FlaskAdmin parameters related to labels for index_view.
        {
            name: description
        }
        """
        return dict([(cm.name, cm.description) for cm in self.bank])

    def add(self, name=None, label=None, description=None):
        assert isinstance(name, str), 'Name must be string, used for attributes'
        self.bank.append(ColumnMeta(name, label, description))

    def get_column_list(self):
        return [cm.name for cm in self.bank]

    def get_column_labels(self):
        return dict([(cm.name, cm.label) for cm in self.bank])


def ranges(loint):
    """Maps [1, 2, 3, 5, 6, 8, 9, 11] -> '1-3, 5-6, 8-9, 11'
    """
    def _ranges(l):
        for a, b in itertools.groupby(enumerate(l), lambda (x, y): y - x):
            b = list(b)
            yield b[0][1], b[-1][1]

    ret = []
    for (start, end) in _ranges(loint):
        if start == end:
            ret.append(str(start))
        else:
            ret.append('%s-%s' % (start, end))

    return ', '.join(ret)


class OrderedDefaultDict(OrderedDict, defaultdict):
    def __init__(self, default_factory=None, *args, **kwargs):
        super(OrderedDefaultDict, self).__init__(*args, **kwargs)
        self.default_factory = default_factory

