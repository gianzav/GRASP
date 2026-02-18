from pytest import fixture
from asp_rewriting.matcher import RuleMatcher
from asp_rewriting.parser import RuleParser
from utils import nospace


def _test_match(pattern, rule, expected):
    parser = RuleParser()
    matcher = RuleMatcher(parser)
    matched = matcher.match(pattern, rule)
    assert matched == expected


def test_match_exact():
    pattern = "a :- b."
    rule = "a :- b."
    expected = ["a", ":-", "b", "."]

    _test_match(pattern, rule, expected)


def test_match_atom_no_arguments():
    pattern = "?head :- b."
    rule = "a :- b."
    expected = ["a", ":-", "b", "."]

    _test_match(pattern, rule, expected)


def test_match_atom_with_arguments():
    pattern = "?head :- b."
    rule = "a(p,X,Y) :- b."
    expected = ["a(p,X,Y)", ":-", "b", "."]

    _test_match(pattern, rule, expected)


def test_match_multiple():
    pattern = "a :- ?body*."
    rule = "a :- b,c,d."
    expected = ["a", ":-", "b,c,d", "."]

    _test_match(pattern, rule, expected)


def test_match_choice():
    pattern = "?h* :- {?rest*}, ?body*."
    rule = "head(X,Y,Z) :- {a}, p, q, r."
    expected = ["head(X,Y,Z)", ":-", "{", "a", "},", "p,q,r", "."]

    _test_match(pattern, rule, expected)


def test_match_cardinality():
    pattern = "?h* :- ?l{?rest*}?u, ?body*."
    rule = "head(X,Y,Z) :- 1{a}2, p, q, r."
    expected = ["head(X,Y,Z)", ":-", "1", "{", "a", "}", "2", ",", "p,q,r", "."]

    _test_match(pattern, rule, expected)


def test_match_pooling():
    pattern = "?h* :- ?l{?rest[;]*}?u, ?body*."
    rule = "head(X,Y,Z) :- 1{a;b;c;d}2, p, q, r."
    expected = [
        "head(X,Y,Z)",
        ":-",
        "1",
        "{",
        "a;b;c;d",
        "}",
        "2",
        ",",
        "p,q,r",
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_match_eager():
    pattern = "head :- ?body* p."
    rule = "head :- a,b,c,p."
    expected = ["head", ":-", "a,b,c,", "p", "."]

    _test_match(pattern, rule, expected)


def test_match_pre_post():
    pattern = "head :- ?bodypre* p, ?bodypost*."
    rule = "head :- a,b,c,p,d,e,f."
    expected = ["head", ":-", "a,b,c,", "p,", "d,e,f", "."]
    _test_match(pattern, rule, expected)


def test_head_choice():
    pattern = "{?h* : ?c*; ?rest[:]*} :- ?body*."
    rule = "{p : q; r : s} :- body."
    expected = ["{", "p", ":", "q", ";", "r:s", "}", ":-", "body", "."]
    _test_match(pattern, rule, expected)


def test_head_cardinality():
    pattern = "?l{?h1* : ?c1*; ?rest[;:,]*}?u :- ?body*."
    rule = "1{p : q; r : s}2 :- body."
    expected = ["1", "{", "p", ":", "q", ";", "r:s", "}", "2", ":-", "body", "."]

    _test_match(pattern, rule, expected)


def test_negative_body_cardinality():
    pattern = "?h* :- ?bodypre* not ?l{?rest[:,;]*}?u, ?body*."
    rule = "head :- p, q, not 1{p:r}2, s, t."
    expected = ["head", ":-", "p,q,", "not", "1", "{", "p:r", "}", "2", ",", "s,t", "."]

    _test_match(pattern, rule, expected)


def test_lower_bound():
    pattern = "?h* :- ?l{?rest[:;,]*}?u, ?body*."
    rule = "head :- 1{p : q; r : s}2, t, u."
    expected = ["head", ":-", "1", "{", "p:q;r:s", "}", "2", ",", "t,u", "."]

    _test_match(pattern, rule, expected)


def test_lower_bound_choice():
    pattern = "?h* :- ?bodypre* ?l{?bi* : ?ci*; ?rest[:;,]*}, ?body*."
    rule = "head :- 1{p : q; c : d}, body."
    expected = [
        "head",
        ":-",
        "",
        "1",
        "{",
        "p",
        ":",
        "q",
        ";",
        "c:d",
        "},",
        "body",
        ".",
    ]

    _test_match(pattern, rule, expected)


def test_atom_list():
    pattern = "?atoms* d."
    rule = "a,b,c,d."
    expected = ["a,b,c,", "d", "."]

    _test_match(pattern, rule, expected)
