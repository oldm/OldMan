import unittest
from default_model import *


class IriTest(unittest.TestCase):
    def tearDown(self):
        tear_down()

    def test_is_blank_node(self):
        bob = create_bob()
        self.assertFalse(bob.is_blank_node())
        alice = lp_model.new()
        self.assertFalse(alice.is_blank_node())

        raoul = lp_model.new(id="http://localhost/.well-known/genid/2387335")
        self.assertTrue(raoul.is_blank_node())

    def test_same_document(self):
        bob = create_bob()
        alice = create_alice()
        self.assertFalse(bob.in_same_document(alice))

        partial_uri = u"http://localhost/persons"
        bob_uri = partial_uri + "#bob"
        bob = lp_model.create(id=bob_uri, name=bob_name, blog=bob_blog, mboxes=bob_emails,
                                         short_bio_en=bob_bio_en, short_bio_fr=bob_bio_fr)
        alice_uri = partial_uri + "#alice"
        alice = lp_model.create(id=alice_uri, name=alice_name, mboxes={alice_mail},
                                           short_bio_en=alice_bio_en)
        self.assertTrue(bob.in_same_document(alice))

    def test_iri_uniqueness(self):
        bob = create_bob()
        bob_iri = bob.id

        with self.assertRaises(OMUniquenessError):
            lp_model.new(id=bob_iri, name=bob_name, mboxes=bob_emails, short_bio_en=u"Will not exist")

        with self.assertRaises(OMUniquenessError):
            lp_model.create(id=bob_iri, name=bob_name, mboxes=bob_emails, short_bio_en=u"Will not exist")

        with self.assertRaises(OMUniquenessError):
            lp_model.new(id=bob_iri, name=bob_name, mboxes=bob_emails, short_bio_en=u"Will not exist", create=True)

        # Forces the creation (by claiming your are not)
        # Dangerous!
        short_bio_en = u"Is forced to exist"
        bob2 = lp_model.new(id=bob_iri, name=bob_name, mboxes=bob_emails, short_bio_en=short_bio_en, is_new=False)
        self.assertEquals(bob2.short_bio_en, short_bio_en)
