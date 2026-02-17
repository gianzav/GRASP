from asp_rewriting.parser import RuleParser
from pytest import fixture


def nospace(s: str):
    return s.replace(" ", "")


@fixture
def parser():
    return RuleParser()


def test_parse_exact_rule(parser):
    rule = "@rule-name a :- b. -> a."

    parsed = parser.parse(rule)

    assert parsed.name == "rule-name"
    assert parsed.pattern == nospace("a :- b.")
    assert parsed.skeletons == [nospace("a.")]


def test_parse_variable_in_pattern(parser):
    rule = "@rule-name ?a :- b. -> a."
    parsed = parser.parse(rule)
