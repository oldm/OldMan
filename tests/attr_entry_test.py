import unittest

from oldman.core.model.attribute import Entry


class AttributeEntryTest(unittest.TestCase):

    def test_1(self):
        entry = Entry()
        value1 = 1

        self.assertNotEquals(entry.current_value, value1)
        entry.current_value = value1
        self.assertEquals(entry.current_value, value1)
        self.assertTrue(entry.has_changed())
        self.assertEquals(entry.diff(), (None, value1))
        self.assertTrue(entry.has_changed())

        entry.receive_storage_ack()
        self.assertFalse(entry.has_changed())

        self.assertEquals(entry.current_value, value1)

        #TODO: use a more precise exception
        with self.assertRaises(Exception):
            entry.diff()

        value2 = 2
        entry.current_value = value2
        self.assertEquals(entry.current_value, value2)
        self.assertTrue(entry.has_changed())
        self.assertEquals(entry.diff(), (value1, value2))

        entry.receive_storage_ack()
        self.assertFalse(entry.has_changed())
        self.assertEquals(entry.current_value, value2)

    def test_boolean(self):
        entry = Entry()
        entry.current_value = False

        self.assertTrue(entry.has_changed())
        self.assertEquals(entry.diff(), (None, False))

        entry.receive_storage_ack()
        self.assertFalse(entry.has_changed())

        entry.current_value = None
        self.assertTrue(entry.has_changed())
        self.assertEquals(entry.diff(), (False, None))

    def test_clone(self):
        value1 = [1]
        value2 = {2}
        e1 = Entry(value1)
        e1.current_value = value2
        self.assertEquals(e1.diff(), (value1, value2))

        e2 = e1.clone()
        self.assertEquals(e1.diff(), e2.diff())

        value3 = {"f": "3"}
        e1.current_value = value3
        self.assertEquals(e1.diff(), (value1, value3))
        self.assertEquals(e2.diff(), (value1, value2))




