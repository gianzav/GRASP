"""
Author: Gianluca Zavan
Email: gianluca.zavan@aau.at
Affiliation: AAU Klagenfurt

Parser for the input language of the term rewriting system.
The parser is able to handle rewriting rules such as:

```
@head-cardinality ?l{?h1 : ?c1*; ?rest*}?u :- ?body*. ->
    % First transform the choice rule
    $h1  :- $c1, $body, not $h1'.
    $h1' :- $c, $body, not $h1.
    {$rest} :- $body. when $rest
    % Add the other rule
    $1($body/vars) :- $l{$h1 : $c1; $rest}$u, $body.
    :- not $1($body/vars), $body.
```

Where
  - ?l, ?h1, ?c1*, ?rest* etc. are pattern variables that can be used for rewriting
  - $h1 etc. are references to such variables in the rewriting
  - Lines starting with % are treated as comments
  - `when` is a keyword that allows to perform a conditional rewriting
"""

from parsy import forward_declaration, regex, seq, string, generate, fail
from dataclasses import dataclass
from asp_rewriting.model import *

# Utilities
whitespace = regex(r"\s*")
lexeme = lambda p: p << whitespace

# Punctuation
lbrace = lexeme(string("{"))
rbrace = lexeme(string("}"))
lbrack = lexeme(string("["))
rbrack = lexeme(string("]"))
colon = lexeme(string(":"))
comma = lexeme(string(","))
at = string("@")
semicolon = lexeme(string(";"))
dot = lexeme(string("."))
arrow = lexeme(string("->"))
impl = lexeme(string(":-"))
newline = lexeme(string("\n"))
question_mark = string("?")
dollar = string("$")

# Primitives

number = lexeme(regex(r"-?(0|[1-9][0-9]*)([.][0-9]+)?([eE][+-]?[0-9]+)?")).map(float)
string_part = regex(r'[^"\\]+')

rule_name = lexeme(at >> regex(r"[A-Za-z\-]+"))
rule_tokens = lexeme(regex(r"[A-Za-z0-9\-\{\},:;()]+"))


def pattern_rule():
    pattern_variable = lexeme(question_mark >> regex(r"[a-z]+[a-z0-9]*")).map(
        PatternVariable
    )
    pattern_variable_collection = lexeme(
        question_mark >> regex(r"[a-z]+[a-z0-9]*") << string("*")
    ).map(PatternVariableCollection)

    pattern_rule_tokens = (
        rule_tokens | pattern_variable_collection | pattern_variable
    ).at_least(1)

    pattern_rule_head = pattern_rule_tokens
    pattern_rule_body = pattern_rule_tokens

    pattern_fact = seq(pattern_rule_head, dot).combine(lambda x, y: x + [y])
    pattern_constraint = seq((impl >> pattern_rule_body), dot).combine(
        lambda x, y: x + [y]
    )
    pattern_full_rule = (pattern_rule_head >> impl) + seq(
        pattern_rule_body, dot
    ).combine(lambda x, y: x + [y])

    return (pattern_constraint | pattern_fact | pattern_full_rule).map(Pattern)


@generate
def skeleton_rule():
    # reference to a pattern variable, e.g. $h
    skeleton_reference_variable = lexeme(dollar >> regex(r"[a-z]+[a-z0-9]*")).map(
        SkeletonVariable
    )

    # extraction of the variables inside a match. E.g. with ?body, $body/vars is
    # expanded to the variables appearing inside whatever was matched in ?body
    skeleton_reference_variable_vars = lexeme(
        dollar >> regex(r"[a-z]+[a-z0-9]*") << string("/vars")
    ).map(SkeletonVariableVarExpansion)

    # numeric variable that denotes a newly generated symbol, e.g. $1
    skeleton_numeric_variable = lexeme(dollar >> regex(r"[0-9]+")).map(
        lambda name: NumberSkeletonVariable(name)
    )

    # named variable that denotes a newly generated symbol, e.g. $[val]
    skeleton_new_named_variable = lexeme(
        dollar >> lbrack >> regex(r"[a-z]+[a-z0-9]*") << rbrack
    ).map(lambda name: NamedSkeletonVariable(name))

    skeleton_variable = (
        skeleton_reference_variable_vars
        | skeleton_reference_variable
        | skeleton_numeric_variable
        | skeleton_new_named_variable
    )

    skeleton_rule_tokens = (rule_tokens | skeleton_variable).at_least(1)

    skeleton_rule_head = skeleton_rule_tokens
    skeleton_rule_body = skeleton_rule_tokens

    skeleton_fact = seq(skeleton_rule_head, dot).combine(lambda x, y: x + [y])
    skeleton_constraint = seq((impl >> skeleton_rule_body), dot).combine(
        lambda x, y: x + [y]
    )
    skeleton_full_rule = (skeleton_rule_head >> impl) + seq(
        skeleton_rule_body, dot
    ).combine(lambda x, y: x + [y])

    _skeleton = yield (skeleton_constraint | skeleton_fact | skeleton_full_rule)

    when = yield (lexeme(string("when")) >> skeleton_variable).optional()

    return Skeleton(_skeleton, when=when)


@generate
def rewriting_rule():
    name = yield whitespace >> rule_name
    pattern = yield pattern_rule()
    yield arrow
    skeletons = yield skeleton_rule.at_least(1)
    return RewritingRule(name, pattern, skeletons)


@dataclass
class RuleParser:

    def parse(self, rule: str) -> RewritingRule:
        return rewriting_rule.parse(rule)
