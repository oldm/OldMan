# -*- coding: utf-8 -*-
"""
    Test property inheritance, isinstance() and issubclass()
"""

from unittest import TestCase
from rdflib import ConjunctiveGraph, URIRef
from ld_orm import default_model_factory
from ld_orm.model import Model
from ld_orm.iri import IncrementalIriGenerator

default_graph = ConjunctiveGraph()
schema_graph = default_graph.get_context(URIRef("http://localhost/schema"))
data_graph = default_graph.get_context(URIRef("http://localhost/data"))

EXAMPLE = "http://localhost/vocab#"

#Turtle instead of JSON-LD because of a bug with the JSON-LD parser
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

# schema_def = {
#     "@context": [
#         {
#             "ex": EXAMPLE,
#         },
#         "http://www.w3.org/ns/hydra/core"
#     ],
#     "@graph": [
#         {
#             "@id": "ex:GrandParentClass",
#             "@type": "hydra:Class",
#             "supportedProperty": [
#                 {
#                     "property": "ex:oldProperty",
#                     "required": False
#                 }
#             ]
#         },
#         {
#             "@id": "ex:ParentClass",
#             "@type": "hydra:Class",
#             "subClassOf": "ex:GrandParentClass",
#             "supportedProperty": [
#                 {
#                     "property": "ex:mediumProperty",
#                     "required": False
#                 }
#             ]
#         },
#         {
#             "@id": "ex:ChildClass",
#             "@type": "hydra:Class",
#             # Saves inference
#             "subClassOf": ["ex:ParentClass", "ex:GrandParentClass"],
#             "supportedProperty": [
#                 {
#                     "property": "ex:newProperty",
#                     "required": False
#                 }
#             ]
#         }
#     ]
# }
#print json.dumps(schema_def)
#schema_graph.parse(data=json.dumps(schema_def), format="json-ld")

schema_graph.parse(data=schema_ttl, format="turtle")
#print schema_graph.serialize(format="n3")

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


model_generator = default_model_factory(schema_graph, default_graph)
# Methods
model_generator.add_method(square_value, "square_value", EXAMPLE + "GrandParentClass")
model_generator.add_method(print_new_value, "print_new_value", EXAMPLE + "ChildClass")
# Method overloading
model_generator.add_method(disclaim1, "disclaim", EXAMPLE + "GrandParentClass")
model_generator.add_method(disclaim2, "disclaim", EXAMPLE + "ParentClass")

# ChildClass is generated before its ancestors!!
child_prefix = "http://localhost/children/"
uri_fragment = "this"

ChildClass = model_generator.generate("ChildClass", context, data_graph,
                                      uri_prefix=child_prefix, uri_fragment=uri_fragment,
                                      incremental_uri=True)
GrandParentClass = model_generator.generate("GrandParentClass", context, data_graph,
                                            uri_prefix="http://localhost/ancestors/",
                                            uri_fragment=uri_fragment)
ParentClass = model_generator.generate("ParentClass", context, data_graph,
                                       uri_prefix="http://localhost/parents/")


class DatatypeTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")
        ChildClass.reset_counter()
        ChildClass.objects.clear_cache()
        ParentClass.objects.clear_cache()
        GrandParentClass.objects.clear_cache()

    def test_types(self):
        john = GrandParentClass()
        jack = ParentClass()
        tom = ChildClass()
        self.assertEquals(john.types,[GrandParentClass.class_uri])
        self.assertEquals(jack.types, [ParentClass.class_uri, GrandParentClass.class_uri])
        self.assertEquals(tom.types, [ChildClass.class_uri, ParentClass.class_uri, GrandParentClass.class_uri])

    def test_ancestor_assignment(self):
        john = GrandParentClass()
        uri = john.id
        old_value = 5
        john.old_number_value = old_value
        # Not declared so will not be saved
        mid_values = {"not saved"}
        john.mid_values = mid_values
        new_value = "not saved (again)"
        john.new_value = new_value
        john.save()
        del john
        GrandParentClass.objects.clear_cache()
        john = GrandParentClass.objects.get(id=uri)
        self.assertEquals(john.old_number_value, old_value)
        with self.assertRaises(AttributeError):
            print john.mid_values
        with self.assertRaises(AttributeError):
            print john.new_value

    def test_parent_assignment(self):
        jack = ParentClass()
        uri = jack.id
        mid_values = {"Hello", "world"}
        jack.mid_values = mid_values
        old_value = 8
        jack.old_number_value = old_value
        new_value = "not saved"
        jack.new_value = new_value
        jack.save()
        del jack
        ParentClass.objects.clear_cache()
        jack = ParentClass.objects.get(id=uri)
        self.assertEquals(jack.mid_values, mid_values)
        self.assertEquals(jack.old_number_value, old_value)
        with self.assertRaises(AttributeError):
            print jack.new_value

    def test_child_assignment(self):
        tom = ChildClass()
        uri = tom.id
        mid_values = {"Hello", "world"}
        tom.mid_values = mid_values
        old_value = 10
        tom.old_number_value = old_value
        new_value = u"ok!"
        tom.new_value = new_value
        tom.save()
        del tom
        ChildClass.objects.clear_cache()
        tom = ChildClass.objects.get(id=uri)
        self.assertEquals(tom.new_value, new_value)
        self.assertEquals(tom.mid_values, mid_values)
        self.assertEquals(tom.old_number_value, old_value)

    def test_isinstance(self):
        john = GrandParentClass.objects.create()
        self.assertTrue(isinstance(john, GrandParentClass))
        self.assertTrue(isinstance(john, Model))
        self.assertTrue(isinstance(john, object))
        self.assertFalse(isinstance(john, ParentClass))
        self.assertFalse(isinstance(john, ChildClass))

        jack = ParentClass.objects.create()
        self.assertTrue(isinstance(jack, ParentClass))
        self.assertTrue(isinstance(jack, GrandParentClass))
        self.assertTrue(isinstance(jack, Model))
        self.assertTrue(isinstance(jack, object))
        self.assertFalse(isinstance(jack, ChildClass))

        tom = ChildClass.objects.create()
        self.assertTrue(isinstance(tom, ChildClass))
        self.assertTrue(isinstance(tom, ParentClass))
        self.assertTrue(isinstance(tom, GrandParentClass))
        self.assertTrue(isinstance(tom, Model))
        self.assertTrue(isinstance(tom, object))

        self.assertFalse(isinstance(5, Model))

    def test_subclass(self):
        self.assertTrue(issubclass(ChildClass, ParentClass))
        self.assertTrue(issubclass(ParentClass, GrandParentClass))
        self.assertTrue(issubclass(ChildClass, GrandParentClass))

        self.assertFalse(issubclass(ParentClass, ChildClass))
        self.assertFalse(issubclass(GrandParentClass, ParentClass))
        self.assertFalse(issubclass(GrandParentClass, ChildClass))

        self.assertTrue(issubclass(ChildClass, Model))
        self.assertTrue(issubclass(ParentClass, Model))
        self.assertTrue(issubclass(GrandParentClass, Model))

        self.assertTrue(issubclass(Model, Model))
        self.assertFalse(issubclass(Model, ChildClass))
        self.assertFalse(issubclass(int, Model))

    def test_square_method(self):
        john = GrandParentClass.objects.create()
        self.assertEquals(john.square_value(), 0)
        john.old_number_value = 5
        self.assertEquals(john.square_value(), 25)
        jack = ParentClass.objects.create()
        self.assertEquals(jack.square_value(), 0)
        jack.old_number_value = 6
        self.assertEquals(jack.square_value(), 36)
        tom = ChildClass.objects.create()
        self.assertEquals(tom.square_value(), 0)
        tom.old_number_value = 7
        self.assertEquals(tom.square_value(), 49)

    def test_new_method(self):
        john = GrandParentClass.objects.create()
        with self.assertRaises(AttributeError):
            john.print_new_value()
        jack = ParentClass.objects.create()
        with self.assertRaises(AttributeError):
            jack.print_new_value()
        tom = ChildClass.objects.create()
        tom.print_new_value()
        tom.new_value = "Hello"
        tom.print_new_value()

    def test_method_overloading(self):
        john = GrandParentClass.objects.create()
        self.assertEquals(john.disclaim(), old_disclaim)
        jack = ParentClass.objects.create()
        self.assertEquals(jack.disclaim(), new_disclaim)
        tom = ChildClass.objects.create()
        self.assertEquals(tom.disclaim(), new_disclaim)

    def test_gets(self):
        john = GrandParentClass.objects.create()
        john_uri = john.id
        jack = ParentClass.objects.create()
        jack_uri = jack.id
        jack_mid_values = {"jack"}
        jack.mid_values = jack_mid_values
        jack.save()
        tom = ChildClass.objects.create()
        tom_uri = tom.id
        tom_new_value = "Tom new value"
        tom.new_value = tom_new_value
        tom.save()
        del john
        del jack
        del tom
        GrandParentClass.objects.clear_cache()
        ParentClass.objects.clear_cache()
        ChildClass.objects.clear_cache()

        tom = GrandParentClass.objects.get_any(id=tom_uri)
        self.assertEquals(tom.new_value, tom_new_value)
        self.assertEquals(tom.disclaim(), new_disclaim)
        self.assertTrue(isinstance(tom, ChildClass))

        jack = GrandParentClass.objects.get_any(id=jack_uri)
        self.assertEquals(jack.mid_values, jack_mid_values)
        self.assertTrue(isinstance(jack, ParentClass))
        self.assertFalse(isinstance(jack, ChildClass))

        john = GrandParentClass.objects.get_any(id=john_uri)
        self.assertTrue(isinstance(john, GrandParentClass))
        self.assertFalse(isinstance(john, ParentClass))
        self.assertFalse(isinstance(john, ChildClass))

    def test_uris(self):
        for i in range(1,6):
            child = ChildClass()
            self.assertEquals(child.id, "%s%d#%s" % (child_prefix, i, uri_fragment))
            print child.id
