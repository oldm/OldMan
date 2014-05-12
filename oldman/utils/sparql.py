def build_query_part(verb_and_vars, subject_term, lines):
    if len(lines) == 0:
        return ""
    query_part = u'%s { \n%s } \n' % (verb_and_vars, lines)
    #{0} -> subject_term
    # format() does not work because other special symbols
    return query_part.replace(u"{0}", subject_term)


def build_update_query_part(verb, subject, lines):
    return build_query_part(verb, u"<%s>" % subject, lines)