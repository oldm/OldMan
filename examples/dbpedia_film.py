"""
Inspired by https://gist.github.com/olberger/c6ebd26bb389e270da72
"""

from rdflib import Graph
from rdflib.plugins.stores.sparqlstore import SPARQLStore
from oldman import ResourceManager
import logging
from os import path


def extract_title(film):
    """French titles first"""
    if len(film.titles) > 0:
        key = "fr" if "fr" in film.titles else film.titles.keys()[0]
        return "%s (%s version)" % (film.titles[key], key)
    return film.id


def extract_name(person):
    """French name first, English second"""
    if person.names is not None and len(person.names) > 0:
        for key in ["fr", "en"]:
            if key in person.names:
                return person.names[key]
        return person.names.values()[0]
    return person.id

if __name__ == "__main__":
    # Main SPARQL requests
    display_some_requests = False
    if display_some_requests:
        logger = logging.getLogger('oldman')
        logger.setLevel(logging.DEBUG)
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        logger.addHandler(sh)

    #schema_url = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/dbpedia_film_schema.ttl"
    schema_url = path.join(path.dirname(__file__), "dbpedia_film_schema.ttl")
    schema_graph = Graph().parse(schema_url, format="turtle")

    #context_url = "https://raw.githubusercontent.com/oldm/OldMan/master/examples/dbpedia_film_context.jsonld"
    context_url = path.join(path.dirname(__file__), "dbpedia_film_context.jsonld")

    data_graph = Graph(SPARQLStore("http://dbpedia.org/sparql", context_aware=False))

    # Resource Manager and Models
    manager = ResourceManager(schema_graph, data_graph)
    film_model = manager.create_model("http://dbpedia.org/ontology/Film", context_url)
    # JSON-LD terms can be used instead of IRIs
    actor_model = manager.create_model("Person", context_url)

    print "10 first French films found on DBPedia"
    print "--------------------------------------"
    for film in film_model.filter(subjects=["http://dbpedia.org/resource/Category:French_films"], limit=10):
        title = extract_title(film)
        if film.actors is None:
            print "   %s %s (no actor declared)" % (title, film.id)
        else:
            actor_names = ", ".join([extract_name(a) for a in film.actors])
            print "   %s starring %s" % (title, actor_names)

    print "Films starring Michel Piccoli"
    print "-----------------------------"
    for film in film_model.filter(actors=["http://dbpedia.org/resource/Michel_Piccoli"]):
        print "   %s" % extract_title(film)