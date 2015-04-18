import unittest
from default_model import *

# Force the cache
data_store.resource_cache.change_cache_region(make_region().configure('dogpile.cache.memory_pickle'))

# With the default implementation they are the same object. FOR TEST ONLY!
resource_mediator = user_mediator


class CacheTest(unittest.TestCase):
    def tearDown(self):
        tear_down()

    def test_direct_cache(self):
        alice1 = lp_model.new(name=alice_name, mboxes={alice_mail}, short_bio_en=alice_bio_en)
        #For test ONLY. Do not do that yourself
        alice_store1 = resource_mediator._conversion_manager.convert_client_to_store_resource(alice1, data_store)
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
        alice1 = create_alice()
        alice2 = user_mediator.get(iri=alice1.id.iri)
        self.assertFalse(alice1 is alice2)
        self.assertEquals(alice1.name, alice2.name)
        self.assertEquals(alice1.id.iri, alice2.id.iri)
        self.assertEquals(alice1.short_bio_en, alice2.short_bio_en)
        self.assertEquals(set(alice1.mboxes), set(alice2.mboxes))

    def test_get_friend(self):
        alice1 = create_alice()
        bob1 = create_bob()
        alice1.friends = {bob1}
        alice1.save()

        alice2 = user_mediator.get(iri=alice1.id.iri)
        self.assertEquals(alice1.id.iri, alice2.id.iri)

        bob2 = list(alice2.friends)[0]
        self.assertFalse(bob1 is bob2)
        self.assertEquals(bob1.name, bob2.name)
        self.assertEquals(bob1.id.iri, bob2.id.iri)
        self.assertEquals(bob1.short_bio_en, bob2.short_bio_en)
        self.assertEquals(set(bob1.mboxes), set(bob2.mboxes))

    def test_modification(self):
        req_name = """ASK { ?x foaf:name "%s"^^xsd:string }"""
        self.assertFalse(bool(data_graph.query(req_name % alice_name)))

        alice1 = create_alice()
        self.assertTrue(bool(data_graph.query(req_name % alice_name)))
        #Not saved modification
        new_name = "New Alice"
        alice1.name = new_name

        alice2 = user_mediator.get(iri=alice1.id.iri)
        self.assertFalse(alice1 is alice2)
        self.assertEquals(alice1.id.iri, alice2.id.iri)
        self.assertNotEquals(alice1.name, alice2.name)
        self.assertEquals(alice2.name, alice_name)

        # Save the modification
        alice1.save()
        self.assertFalse(bool(data_graph.query(req_name % alice_name)))
        self.assertTrue(bool(data_graph.query(req_name % new_name)))

        alice3 = user_mediator.get(iri=alice1.id.iri)
        self.assertFalse(alice1 is alice3)
        self.assertEquals(alice1.id.iri, alice3.id.iri)
        self.assertEquals(alice1.name, alice3.name)
        self.assertEquals(alice3.name, new_name)

        name3 = "Third Alice"
        alice3.name = name3
        alice3.save()
        self.assertFalse(bool(data_graph.query(req_name % new_name)))
        self.assertTrue(bool(data_graph.query(req_name % name3)))

        alice4 = user_mediator.get(iri=alice1.id.iri)
        self.assertFalse(alice3 is alice4)
        self.assertEquals(alice3.id.iri, alice4.id.iri)
        self.assertEquals(alice3.name, alice4.name)
        self.assertEquals(alice4.name, name3)

    def test_basic_deletion(self):
        alice1 = create_alice()
        alice_iri = alice1.id.iri
        alice1.delete()

        alice2 = user_mediator.get(iri=alice_iri)
        self.assertEquals(alice2.types, [])

    def test_delete_from_cache(self):
        alice1 = create_alice()
        alice_iri = alice1.id.iri

        alice2 = user_mediator.get(iri=alice_iri)
        alice2.delete()

        alice3 = user_mediator.get(iri=alice_iri)
        self.assertEquals(alice3.types, [])
        self.assertFalse(bool(data_graph.query("ASK { <%s> ?p ?o }" % alice_iri)))