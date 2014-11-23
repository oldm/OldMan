# -*- coding: utf-8 -*-
"""
    Test property inheritance, isinstance() and issubclass()
"""

from unittest import TestCase
from rdflib import ConjunctiveGraph, URIRef
from oldman import ClientResourceManager, parse_graph_safely, SPARQLDataStore

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


data_store = SPARQLDataStore(data_graph, schema_graph=schema_graph)
manager = ClientResourceManager(data_store)
# Methods
manager.declare_method(square_value, "square_value", EXAMPLE + "GrandParentClass")
manager.declare_method(print_new_value, "print_new_value", EXAMPLE + "ChildClass")
# Method overloading
manager.declare_method(disclaim1, "disclaim", EXAMPLE + "GrandParentClass")
manager.declare_method(disclaim2, "disclaim", EXAMPLE + "ParentClass")

# ChildClass is generated before its ancestors!!
child_prefix = "http://localhost/children/"
uri_fragment = "this"

child_model = manager.create_model("ChildClass", context, iri_prefix=child_prefix, iri_fragment=uri_fragment,
                                   incremental_iri=True)
grand_parent_model = manager.create_model("GrandParentClass", context, iri_prefix="http://localhost/ancestors/",
                                          iri_fragment=uri_fragment)
parent_model = manager.create_model("ParentClass", context, iri_prefix="http://localhost/parents/")


class InstanceTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")
        child_model.reset_counter()

    def test_types(self):
        john = grand_parent_model.new()
        jack = parent_model.new()
        tom = child_model.new()
        self.assertEquals(john.types, [grand_parent_model.class_iri])
        self.assertEquals(jack.types, [parent_model.class_iri, grand_parent_model.class_iri])
        self.assertEquals(tom.types, [child_model.class_iri, parent_model.class_iri, grand_parent_model.class_iri])

    def test_ancestor_assignment(self):
        john = grand_parent_model.new()
        uri = john.id
        old_value = 5
        john.old_number_value = old_value
        john.save()
        with self.assertRaises(AttributeError):
            john.mid_values = {"not saved"}
        with self.assertRaises(AttributeError):
            john.new_value = "not saved (again)"
        john = grand_parent_model.get(id=uri)
        self.assertEquals(john.old_number_value, old_value)
        with self.assertRaises(AttributeError):
            print john.mid_values
        with self.assertRaises(AttributeError):
            print john.new_value

    def test_parent_assignment(self):
        jack = parent_model.new()
        uri = jack.id
        mid_values = {"Hello", "world"}
        jack.mid_values = mid_values
        old_value = 8
        jack.old_number_value = old_value
        with self.assertRaises(AttributeError):
            jack.new_value = "not saved"
        jack.save()
        jack = parent_model.get(id=uri)
        self.assertEquals(jack.mid_values, mid_values)
        self.assertEquals(jack.old_number_value, old_value)
        with self.assertRaises(AttributeError):
            print jack.new_value

    def test_child_assignment(self):
        tom = child_model.new()
        uri = tom.id
        mid_values = {"Hello", "world"}
        tom.mid_values = mid_values
        old_value = 10
        tom.old_number_value = old_value
        new_value = u"ok!"
        tom.new_value = new_value
        tom.save()
        tom = child_model.get(id=uri)
        self.assertEquals(tom.new_value, new_value)
        self.assertEquals(tom.mid_values, mid_values)
        self.assertEquals(tom.old_number_value, old_value)

    def test_isinstance(self):
        john = grand_parent_model.create()
        self.assertTrue(john.is_instance_of(grand_parent_model))
        self.assertFalse(john.is_instance_of(parent_model))
        self.assertFalse(john.is_instance_of(child_model))

        jack = parent_model.create()
        self.assertTrue(jack.is_instance_of(parent_model))
        self.assertTrue(jack.is_instance_of(grand_parent_model))
        self.assertFalse(jack.is_instance_of(child_model))

        tom = child_model.create()
        self.assertTrue(tom.is_instance_of(child_model))
        self.assertTrue(tom.is_instance_of(parent_model))
        self.assertTrue(tom.is_instance_of(grand_parent_model))

    def test_subclass(self):
        self.assertTrue(child_model.is_subclass_of(parent_model))
        self.assertTrue(parent_model.is_subclass_of(grand_parent_model))
        self.assertTrue(child_model.is_subclass_of(grand_parent_model))

        self.assertFalse(parent_model.is_subclass_of(child_model))
        self.assertFalse(grand_parent_model.is_subclass_of(parent_model))
        self.assertFalse(grand_parent_model.is_subclass_of(child_model))

    def test_square_method(self):
        john = grand_parent_model.create()
        self.assertEquals(john.square_value(), 0)
        john.old_number_value = 5
        self.assertEquals(john.square_value(), 25)
        jack = parent_model.create()
        self.assertEquals(jack.square_value(), 0)
        jack.old_number_value = 6
        self.assertEquals(jack.square_value(), 36)
        tom = child_model.create()
        self.assertEquals(tom.square_value(), 0)
        tom.old_number_value = 7
        self.assertEquals(tom.square_value(), 49)

    def test_new_method(self):
        john = grand_parent_model.create()
        with self.assertRaises(AttributeError):
            john.print_new_value()
        jack = parent_model.create()
        with self.assertRaises(AttributeError):
            jack.print_new_value()
        tom = child_model.create()
        tom.print_new_value()
        tom.new_value = "Hello"
        tom.print_new_value()

    def test_method_overloading(self):
        john = grand_parent_model.create()
        self.assertEquals(john.disclaim(), old_disclaim)
        jack = parent_model.create()
        self.assertEquals(jack.disclaim(), new_disclaim)
        tom = child_model.create()
        self.assertEquals(tom.disclaim(), new_disclaim)

    def test_gets(self):
        john = grand_parent_model.create()
        john_uri = john.id
        jack = parent_model.create()
        jack_uri = jack.id
        jack_mid_values = {"jack"}
        jack.mid_values = jack_mid_values
        jack.save()
        tom = child_model.create()
        tom_uri = tom.id
        tom_new_value = "Tom new value"
        tom.new_value = tom_new_value
        tom.save()

        tom = manager.get(id=tom_uri)
        self.assertEquals(tom.new_value, tom_new_value)
        self.assertEquals(tom.disclaim(), new_disclaim)
        self.assertTrue(tom.is_instance_of(child_model))

        jack = manager.get(id=jack_uri)
        self.assertEquals(jack.mid_values, jack_mid_values)
        self.assertTrue(jack.is_instance_of(parent_model))
        self.assertFalse(jack.is_instance_of(child_model))

        john = manager.get(id=john_uri)
        self.assertTrue(john.is_instance_of(grand_parent_model))
        self.assertFalse(john.is_instance_of(parent_model))
        self.assertFalse(john.is_instance_of(child_model))

    def test_uris(self):
        for i in range(1, 6):
            child = child_model.new()
            self.assertEquals(child.id, "%s%d#%s" % (child_prefix, i, uri_fragment))
            print child.id