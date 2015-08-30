# -*- coding: utf-8 -*-
"""
    Test property inheritance, isinstance() and issubclass()
"""

from unittest import TestCase
from rdflib import ConjunctiveGraph, URIRef
from oldman import create_user_mediator, parse_graph_safely, SparqlStore

default_graph = ConjunctiveGraph()
schema_graph = default_graph.get_context(URIRef("http://localhost/schema"))
data_graph = default_graph.get_context(URIRef("http://localhost/data"))

EXAMPLE = "http://localhost/vocab#"

schema_ttl = """
@prefix ex: <%s> .
@prefix hydra: <http://www.w3.org/ns/hydra/core#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:GrandParentClass a hydra:Class ;
    hydra:supportedProperty [
        hydra:property ex:oldProperty
    ] .

ex:ParentClass a hydra:Class ;
    rdfs:subClassOf ex:GrandParentClass ;
    hydra:supportedProperty [
        hydra:property ex:mediumProperty
    ] .

ex:ChildClass a hydra:Class ;
    rdfs:subClassOf ex:ParentClass, ex:GrandParentClass ;
    hydra:supportedProperty [
        hydra:property ex:newProperty
    ] .
""" % format(EXAMPLE)

parse_graph_safely(schema_graph, data=schema_ttl, format="turtle")

context = {
    "@context": {
        "ex": EXAMPLE,
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "id": "@id",
        "type": "@type",
        "ChildClass": "ex:ChildClass",
        "ParentClass": "ex:ParentClass",
        "GrandParentClass": "ex:GrandParentClass",
        "old_number_value": {
            "@id": "ex:oldProperty",
            "@type": "xsd:int"
        },
        "mid_values": {
            "@id": "ex:mediumProperty",
            "@type": "xsd:string",
            "@container": "@set"
        },
        "new_value": {
            "@id": "ex:newProperty",
            "@type": "xsd:string"
        }
    }
}

old_disclaim = "Old disclam"
new_disclaim = "New disclam"


def square_value(self):
    if self.old_number_value is None:
        return 0
    return self.old_number_value**2


def print_new_value(self):
    print self.new_value


def disclaim1(self):
    return old_disclaim


def disclaim2(self):
    return new_disclaim


data_store = SparqlStore(data_graph, schema_graph=schema_graph)
# ChildClass is generated before its ancestors!!
child_prefix = "http://localhost/children/"
uri_fragment = "this"
data_store.create_model("ChildClass", context, iri_prefix=child_prefix, iri_fragment=uri_fragment, incremental_iri=True)
data_store.create_model("GrandParentClass", context, iri_prefix="http://localhost/ancestors/",
                        iri_fragment=uri_fragment)
data_store.create_model("ParentClass", context, iri_prefix="http://localhost/parents/")


user_mediator = create_user_mediator(data_store, schema_graph=schema_graph)
user_mediator.import_store_models()
# Methods
user_mediator.declare_method(square_value, "square_value", EXAMPLE + "GrandParentClass")
user_mediator.declare_method(print_new_value, "print_new_value", EXAMPLE + "ChildClass")
# Method overloading
user_mediator.declare_method(disclaim1, "disclaim", EXAMPLE + "GrandParentClass")
user_mediator.declare_method(disclaim2, "disclaim", EXAMPLE + "ParentClass")

child_model = user_mediator.get_client_model("ChildClass")
grand_parent_model = user_mediator.get_client_model("GrandParentClass")
parent_model = user_mediator.get_client_model("ParentClass")

# Only for reset the counter
child_store_model = data_store.model_manager.get_model(child_model.class_iri)


class InstanceTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")
        child_store_model.reset_counter()

    def test_types(self):
        session1 = user_mediator.create_session()
        john = grand_parent_model.new(session1)
        jack = parent_model.new(session1)
        tom = child_model.new(session1)
        self.assertEquals(john.types, [grand_parent_model.class_iri])
        self.assertEquals(jack.types, [parent_model.class_iri, grand_parent_model.class_iri])
        self.assertEquals(tom.types, [child_model.class_iri, parent_model.class_iri, grand_parent_model.class_iri])
        session1.close()

    def test_ancestor_assignment(self):
        session1 = user_mediator.create_session()
        john = grand_parent_model.new(session1)
        old_value = 5
        john.old_number_value = old_value
        session1.flush()
        iri = john.id.iri
        with self.assertRaises(AttributeError):
            john.mid_values = {"not saved"}
        with self.assertRaises(AttributeError):
            john.new_value = "not saved (again)"
        session1.close()

        session2 = user_mediator.create_session()
        john2 = grand_parent_model.get(session2, iri=iri)
        self.assertEquals(john2.old_number_value, old_value)
        with self.assertRaises(AttributeError):
            print john2.mid_values
        with self.assertRaises(AttributeError):
            print john2.new_value
        session2.close()

    def test_parent_assignment(self):
        session1 = user_mediator.create_session()
        jack = parent_model.new(session1)
        mid_values = {"Hello", "world"}
        jack.mid_values = mid_values
        old_value = 8
        jack.old_number_value = old_value
        with self.assertRaises(AttributeError):
            jack.new_value = "not saved"
        session1.flush()
        uri = jack.id.iri
        session1.close()

        session2 = user_mediator.create_session()
        jack2 = parent_model.get(session2, iri=uri)
        self.assertEquals(jack2.mid_values, mid_values)
        self.assertEquals(jack2.old_number_value, old_value)
        with self.assertRaises(AttributeError):
            print jack2.new_value
        session2.close()

    def test_child_assignment(self):
        session1 = user_mediator.create_session()
        tom = child_model.new(session1)
        mid_values = {"Hello", "world"}
        tom.mid_values = mid_values
        old_value = 10
        tom.old_number_value = old_value
        new_value = u"ok!"
        tom.new_value = new_value
        session1.flush()
        uri = tom.id.iri
        session1.close()

        session2 = user_mediator.create_session()
        tom2 = child_model.get(session2, iri=uri)
        self.assertEquals(tom2.new_value, new_value)
        self.assertEquals(tom2.mid_values, mid_values)
        self.assertEquals(tom2.old_number_value, old_value)
        session2.close()

    def test_isinstance(self):
        session1 = user_mediator.create_session()
        john = grand_parent_model.new(session1)
        session1.flush()
        self.assertTrue(john.is_instance_of(grand_parent_model))
        self.assertFalse(john.is_instance_of(parent_model))
        self.assertFalse(john.is_instance_of(child_model))

        jack = parent_model.new(session1)
        session1.flush()
        self.assertTrue(jack.is_instance_of(parent_model))
        self.assertTrue(jack.is_instance_of(grand_parent_model))
        self.assertFalse(jack.is_instance_of(child_model))

        tom = child_model.new(session1)
        session1.flush()
        self.assertTrue(tom.is_instance_of(child_model))
        self.assertTrue(tom.is_instance_of(parent_model))
        self.assertTrue(tom.is_instance_of(grand_parent_model))
        session1.close()

    def test_subclass(self):
        self.assertTrue(child_model.is_subclass_of(parent_model))
        self.assertTrue(parent_model.is_subclass_of(grand_parent_model))
        self.assertTrue(child_model.is_subclass_of(grand_parent_model))

        self.assertFalse(parent_model.is_subclass_of(child_model))
        self.assertFalse(grand_parent_model.is_subclass_of(parent_model))
        self.assertFalse(grand_parent_model.is_subclass_of(child_model))

    def test_square_method(self):
        session1 = user_mediator.create_session()
        john = grand_parent_model.new(session1)
        self.assertEquals(john.square_value(), 0)
        john.old_number_value = 5
        self.assertEquals(john.square_value(), 25)
        jack = parent_model.new(session1)
        self.assertEquals(jack.square_value(), 0)
        jack.old_number_value = 6
        self.assertEquals(jack.square_value(), 36)
        tom = child_model.new(session1)
        self.assertEquals(tom.square_value(), 0)
        tom.old_number_value = 7
        self.assertEquals(tom.square_value(), 49)
        session1.close()

    def test_new_method(self):
        session1 = user_mediator.create_session()
        john = grand_parent_model.new(session1)
        with self.assertRaises(AttributeError):
            john.print_new_value()
        jack = parent_model.new(session1)
        with self.assertRaises(AttributeError):
            jack.print_new_value()
        tom = child_model.new(session1)
        tom.print_new_value()
        tom.new_value = "Hello"
        tom.print_new_value()
        session1.close()

    def test_method_overloading(self):
        session1 = user_mediator.create_session()
        john = grand_parent_model.new(session1)
        self.assertEquals(john.disclaim(), old_disclaim)
        jack = parent_model.new(session1)
        self.assertEquals(jack.disclaim(), new_disclaim)
        tom = child_model.new(session1)
        self.assertEquals(tom.disclaim(), new_disclaim)
        session1.close()

    def test_gets(self):
        session1 = user_mediator.create_session()
        john = grand_parent_model.new(session1)
        jack = parent_model.new(session1)
        jack_mid_values = {"jack"}
        jack.mid_values = jack_mid_values
        tom = child_model.new(session1)
        tom_new_value = "Tom new value"
        tom.new_value = tom_new_value
        session1.flush()
        john_uri = john.id.iri
        jack_uri = jack.id.iri
        tom_uri = tom.id.iri

        session2 = user_mediator.create_session()
        tom2 = session2.get(iri=tom_uri)
        self.assertEquals(tom2.new_value, tom_new_value)
        self.assertEquals(tom2.disclaim(), new_disclaim)
        self.assertTrue(tom2.is_instance_of(child_model))
        session2.close()

        session3 = user_mediator.create_session()
        jack2 = session3.get(iri=jack_uri)
        self.assertEquals(jack2.mid_values, jack_mid_values)
        self.assertTrue(jack2.is_instance_of(parent_model))
        self.assertFalse(jack2.is_instance_of(child_model))
        session3.close()

        session4 = user_mediator.create_session()
        john2 = session4.get(iri=john_uri)
        self.assertTrue(john2.is_instance_of(grand_parent_model))
        self.assertFalse(john2.is_instance_of(parent_model))
        self.assertFalse(john2.is_instance_of(child_model))
        session4.close()
        session1.close()

    def test_uris(self):
        for i in range(1, 6):
            session = user_mediator.create_session()
            child = child_model.new(session)
            session.flush()
            self.assertEquals(child.id.iri, "%s%d#%s" % (child_prefix, i, uri_fragment))
            print child.id.iri
            session.close()