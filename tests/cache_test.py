import unittest
from default_model import *

# Force the cache
from oldman.session.tracker import BasicResourceTracker

data_store.resource_cache.change_cache_region(make_region().configure('dogpile.cache.memory_pickle'))

# With the default implementation they are the same object. FOR TEST ONLY!
resource_mediator = user_mediator


class CacheTest(unittest.TestCase):
    def tearDown(self):
        tear_down()

    def test_direct_cache(self):
        session = user_mediator.create_session()
        alice1 = lp_model.new(session, name=alice_name, mboxes={alice_mail}, short_bio_en=alice_bio_en)
        #For test ONLY. Do not do that yourself
        store_tracker = BasicResourceTracker()
        alice_store1 = resource_mediator._conversion_manager.convert_client_to_store_resource(alice1, data_store,
                                                                                              store_tracker)
        data_store.resource_cache.set_resource(alice_store1)
        alice2 = data_store.resource_cache.get_resource(alice_store1.id.iri)
        self.assertFalse(alice1 is alice2)
        self.assertEquals(alice1.name, alice2.name)
        #Not true anymore because of temporary IRI.
        #self.assertEquals(alice1.id.iri, alice2.id.iri)
        self.assertEquals(alice1.short_bio_en, alice2.short_bio_en)
        self.assertEquals(set(alice1.mboxes), set(alice2.mboxes))

        data_store.resource_cache.remove_resource(alice1)
        self.assertFalse(data_store.resource_cache.get_resource(alice1.id.iri))

    def test_simple_get(self):
        session1 = user_mediator.create_session()
        alice1 = create_alice(session1)

        session2 = user_mediator.create_session()
        alice2 = session2.get(iri=alice1.id.iri)
        self.assertFalse(alice1 is alice2)
        self.assertEquals(alice1.name, alice2.name)
        self.assertEquals(alice1.id.iri, alice2.id.iri)
        self.assertEquals(alice1.short_bio_en, alice2.short_bio_en)
        self.assertEquals(set(alice1.mboxes), set(alice2.mboxes))
        session1.close()
        session2.close()

    def test_get_friend(self):
        session = user_mediator.create_session()
        alice1 = create_alice(session)
        bob1 = create_bob(session)
        alice1.friends = {bob1}
        session.flush()

        alice2 = session.get(iri=alice1.id.iri)
        self.assertEquals(alice1.id.iri, alice2.id.iri)

        bob2 = list(alice2.friends)[0]
        #self.assertFalse(bob1 is bob2)
        self.assertEquals(bob1.name, bob2.name)
        self.assertEquals(bob1.id.iri, bob2.id.iri)
        self.assertEquals(bob1.short_bio_en, bob2.short_bio_en)
        self.assertEquals(set(bob1.mboxes), set(bob2.mboxes))

    def test_modification(self):
        session1 = user_mediator.create_session()
        req_name = """ASK { ?x foaf:name "%s"^^xsd:string }"""
        self.assertFalse(bool(data_graph.query(req_name % alice_name)))

        alice1 = create_alice(session1)
        self.assertTrue(bool(data_graph.query(req_name % alice_name)))
        #Not saved modification
        new_name = "New Alice"
        alice1.name = new_name

        session2 = user_mediator.create_session()
        alice2 = session2.get(iri=alice1.id.iri)
        self.assertFalse(alice1 is alice2)
        self.assertEquals(alice1.id.iri, alice2.id.iri)
        self.assertNotEquals(alice1.name, alice2.name)
        self.assertEquals(alice2.name, alice_name)

        # Save the modification of alice1
        session1.flush()
        self.assertFalse(bool(data_graph.query(req_name % alice_name)))
        self.assertTrue(bool(data_graph.query(req_name % new_name)))

        session3 = user_mediator.create_session()
        alice3 = session3.get(iri=alice1.id.iri)
        self.assertFalse(alice1 is alice3)
        self.assertEquals(alice1.id.iri, alice3.id.iri)
        self.assertEquals(alice1.name, alice3.name)
        self.assertEquals(alice3.name, new_name)

        name3 = "Third Alice"
        alice3.name = name3
        session3.flush()
        self.assertFalse(bool(data_graph.query(req_name % new_name)))
        self.assertTrue(bool(data_graph.query(req_name % name3)))

        session4 = user_mediator.create_session()
        alice4 = session4.get(iri=alice1.id.iri)
        self.assertFalse(alice3 is alice4)
        self.assertEquals(alice3.id.iri, alice4.id.iri)
        self.assertEquals(alice3.name, alice4.name)
        self.assertEquals(alice4.name, name3)
        session1.close()
        session2.close()
        session3.close()
        session4.close()

    def test_basic_deletion(self):
        session1 = user_mediator.create_session()
        alice1 = create_alice(session1)
        alice_iri = alice1.id.iri
        session1.delete(alice1)
        session1.flush()
        session1.close()

        session2 = user_mediator.create_session()
        alice2 = session2.get(iri=alice_iri)
        self.assertEquals(alice2.types, [])
        session2.close()

    def test_delete_from_cache(self):
        session1 = user_mediator.create_session()
        alice1 = create_alice(session1)
        alice_iri = alice1.id.iri
        session1.close()

        session2 = user_mediator.create_session()
        alice2 = session2.get(iri=alice_iri)
        session2.delete(alice2)
        session2.flush()
        session2.close()

        session3 = user_mediator.create_session()
        alice3 = session3.get(iri=alice_iri)
        self.assertEquals(alice3.types, [])
        self.assertFalse(bool(data_graph.query("ASK { <%s> ?p ?o }" % alice_iri)))
        session3.close()
