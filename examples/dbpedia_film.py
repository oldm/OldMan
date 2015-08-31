"""
Inspired by https://gist.github.com/olberger/c6ebd26bb389e270da72 .

See http://oldman.readthedocs.org/en/latest/examples/dbpedia.html .
"""

from rdflib import Graph
from rdflib.plugins.stores.sparqlstore import SPARQLStore as RdflibSPARQLStore
from oldman import create_user_mediator, SparqlStore
from dogpile.cache import make_region
import logging
from os import path
import time


def extract_title(film):
    """French titles first"""
    if len(film.titles) > 0:
        key = "fr" if "fr" in film.titles else film.titles.keys()[0]
        return "%s (%s version)" % (film.titles[key], key)
    return film.id


def extract_name(person):
    """French name first, English second"""
    # Sometimes the DBpedia entries are very incomplete: few actors are not known to be persons...
    # Thus no name can then be extracted
    if "http://xmlns.com/foaf/0.1/Person" not in person.types:
        return None

    if person.names is not None and len(person.names) > 0:
        for key in ["fr", "en"]:
            if key in person.names:
                return person.names[key]
        return person.names.values()[0]
    return person.id.iri

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

    data_graph = Graph(RdflibSPARQLStore("http://dbpedia.org/sparql", context_aware=False))

    cache_region = make_region().configure('dogpile.cache.memory_pickle')

    # store: SPARQL-aware triple store, with two models
    store = SparqlStore(data_graph, schema_graph=schema_graph, cache_region=cache_region)
    store.create_model("http://dbpedia.org/ontology/Film", context_url)
    # JSON-LD terms can be used instead of IRIs
    store.create_model("Person", context_url)

    # Mediator for users
    user_mediator = create_user_mediator(store)
    # Re-uses the models of the data store
    user_mediator.import_store_models()
    film_model = user_mediator.get_client_model("http://dbpedia.org/ontology/Film")
    actor_model = user_mediator.get_client_model("Person")

    print "10 first French films found on DBPedia (with OldMan)"
    print "----------------------------------------------------"
    q1_start_time = time.time()
    session = user_mediator.create_session()
    for film in film_model.filter(session, subjects=["http://dbpedia.org/resource/Category:French_films"],
                                  limit=10
                                  , eager=True, pre_cache_properties=["http://dbpedia.org/ontology/starring"]
                                  ):
        title = extract_title(film)
        if film.actors is None:
            print "   %s %s (no actor declared)" % (title, film.id)
        else:
            actor_names = ", ".join([extract_name(a) for a in film.actors])
            print "   %s starring %s" % (title, actor_names)
    print "Done in %.3f seconds" % (time.time() - q1_start_time)

    print "Again, with the cache:"
    q1_start_time = time.time()
    for film in film_model.filter(session, subjects=["http://dbpedia.org/resource/Category:French_films"],
                                  limit=10
                                  #, eager=True, pre_cache_properties=["http://dbpedia.org/ontology/starring"]
                                  ):
        title = extract_title(film)
        if film.actors is not None:
            [extract_name(a) for a in film.actors]
    print "Done in %.3f seconds" % (time.time() - q1_start_time)

    print "Films starring Michel Piccoli (with OldMan)"
    print "-------------------------------------------"
    q2_start_time = time.time()
    for film in film_model.filter(session, actors=["http://dbpedia.org/resource/Michel_Piccoli"]
                                  , eager=True
                                  ):
        print "   %s" % extract_title(film)
    print "Done in %.3f seconds" % (time.time() - q2_start_time)
    session.close()

    print "10 first French films found on DBPedia (without OldMan)"
    print "-------------------------------------------------------"
    q3_start_time = time.time()
    results = data_graph.query("""
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dbpo: <http://dbpedia.org/ontology/>

    SELECT ?film ?title_fr ?title_en ?actor ?actor_name_fr ?actor_name_en
    WHERE {
        {
         SELECT ?film
         WHERE {
            ?film a dbpo:Film ;
                  dcterms:subject <http://dbpedia.org/resource/Category:French_films> .
          }
          LIMIT 10
        }
        OPTIONAL {
           ?film rdfs:label ?title_en .
           FILTER langMatches( lang(?title_en), "EN" ) .
        }
        OPTIONAL {
           ?film rdfs:label ?title_fr .
           FILTER langMatches( lang(?title_fr), "FR" ) .
        }
        OPTIONAL {
          ?film dbpo:starring ?actor .
          OPTIONAL {
            ?actor foaf:name ?actor_name_en .
            FILTER langMatches( lang(?actor_name_en), "EN" ) .
          }
          OPTIONAL {
            ?actor foaf:name ?actor_name_fr .
            FILTER langMatches( lang(?actor_name_fr), "FR" ) .
          }
        }
    }
    """)
    # Extract titles and names
    film_titles = {}
    film_actors = {}
    for film_iri, title_fr, title_en, actor_iri, actor_name_fr, actor_name_en in results:
        if film_iri not in film_titles:
            for t in [title_fr, title_en, film_iri]:
                if t is not None:
                    film_titles[film_iri] = unicode(t)
                    break
        for name in [actor_name_fr, actor_name_en, actor_iri]:
            if name is not None:
                if film_iri not in film_actors:
                    film_actors[film_iri] = [name]
                elif name not in film_actors[film_iri]:
                    film_actors[film_iri].append(unicode(name))
                break
    # Display titles and names
    for film_iri in film_titles:
        title = film_titles[film_iri]
        if film_iri not in film_actors:
            print "   %s %s (no actor declared)" % (title, film_iri)
        else:
            actor_names = ", ".join(film_actors[film_iri])
            print "   %s with %s" % (title, actor_names)
    print "Done in %.3f seconds" % (time.time() - q3_start_time)

    print "Films starring Michel Piccoli (without OldMan)"
    print "----------------------------------------------"
    q4_start_time = time.time()
    results = data_graph.query("""
    PREFIX foaf: <http://xmlns.com/foaf/0.1/>
    PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dbpo: <http://dbpedia.org/ontology/>

    SELECT ?film ?title_fr ?title_en
    WHERE {
        ?film a dbpo:Film ;
              dbpo:starring <http://dbpedia.org/resource/Michel_Piccoli> .
        OPTIONAL {
           ?film rdfs:label ?title_en .
           FILTER langMatches( lang(?title_en), "EN" ) .
        }
        OPTIONAL {
           ?film rdfs:label ?title_fr .
           FILTER langMatches( lang(?title_fr), "FR" ) .
        }
    }
    """)
    for film_iri, title_fr, title_en in results:
        if film_iri not in film_titles:
            for t in [title_fr, title_en, film_iri]:
                if t is not None:
                    print "    %s" % t
                    break
    print "Done in %.3f seconds" % (time.time() - q4_start_time)