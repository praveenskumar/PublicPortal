
import datetime
import unittest

from portal.account.widgets import get_shift_start_dt


class DTTest(unittest.TestCase):

    def test(self):
        L = [1, 4, 9, 13, 17, 21]
        self.assertEqual(get_shift_start_dt(L, datetime.datetime(2018, 3, 14, 19, 56, 00)),
                                         datetime.datetime(2018, 3, 14, 17, 00, 00))
        self.assertEqual(get_shift_start_dt(L, datetime.datetime(2018, 3, 14, 12, 49, 00)),
                                         datetime.datetime(2018, 3, 14, 9, 00, 00))
        self.assertEqual(get_shift_start_dt(L, datetime.datetime(2018, 3, 14, 23, 59, 00)),
                                         datetime.datetime(2018, 3, 14, 21, 00, 00))
        self.assertEqual(get_shift_start_dt(L, datetime.datetime(2018, 3, 15, 00, 30, 00)),
                                         datetime.datetime(2018, 3, 14, 21, 00, 00))


if __name__ == '__main__':
    unittest.main()

