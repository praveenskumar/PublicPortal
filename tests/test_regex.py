
import unittest

from portal.api.eve import parse_currency, parse_numeral


class RegexTest(unittest.TestCase):

    def _test(self, s, currency, numeral):
        self.assertEqual(parse_currency(s), currency)
        self.assertEqual(parse_numeral(s), numeral)

    def test_numeral(self):
        self._test('$1', '$', 1.00)
        self._test('$1.1', '$', 1.10)
        self._test('$1.00', '$', 1.00)

        self._test('$100', '$', 100)
        self._test('$100.1', '$', 100.1)
        self._test('$100.12', '$', 100.12)

        self._test('$1,000', '$', 1000)
        self._test('$1,000.1', '$', 1000.1)
        self._test('$1,000.12', '$', 1000.12)
        self._test('$789.16', '$', 789.16)

    def test_currency(self):
        self._test(u'CN\xa51.00', u'CN\xa5', 1.00)
        self._test(u'CN\xa512.00', u'CN\xa5', 12.00)
        self._test(u'CN\xa5123.00', u'CN\xa5', 123.00)
        self._test(u'CN\xa51,234.00', u'CN\xa5', 1234.00)
        self._test(u'$1,400.00', u'$', 1400.00)


if __name__ == '__main__':
    unittest.main()

