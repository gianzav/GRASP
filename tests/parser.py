from asp_rewriting.parser import RuleParser
from pytest import fixture


def nospace(s: str):
    return s.replace(" ", "")


@fixture
def parser():
    return RuleParser()


def test_parse_exact_rule(parser):
    rule = "@rule-name a :- b. -> a."
    parser.parse(rule)


def test_parse_variable_in_pattern(parser):
    rule = "@rule-name ?a :- b. -> a."
    parser.parse(rule)


def test_parse_variable_collection_in_pattern(parser):
    rule = "@rule-name ?a :- ?body*. -> a."
    parser.parse(rule)


def test_skeleton_variables(parser):
    rule = "@rule-name ?a :- ?b, ?body*. -> $[new] :- $b, $1."
    parser.parse(rule)


def test_multiple_skeletons(parser):
    rule = """\
    @rule-name ?a :- ?b, ?body*. -> 
        p :- $a.
        $[new] :- $b, $1.
    """
    parser.parse(rule)


def test_skeleton_variable_vars(parser):
    rule = """\
    @rule-name ?a :- ?b, ?body*. -> 
        p($body/vars) :- q.
    """
    parser.parse(rule)


def test_when(parser):
    rule = """\
    @rule-name ?a :- ?b, ?body*. -> 
        {p} :- $body. when $body
    """
    parser.parse(rule)
