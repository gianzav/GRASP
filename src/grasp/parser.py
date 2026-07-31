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

from parsy import forward_declaration, regex, seq, string, generate, fail, string_from
from dataclasses import dataclass
from grasp.model import *

# Utilities
whitespace = regex(r"\s*")
whitespace_no_nl = regex(r"[ \t]*")  # Spaces and tabs only, no newlines
lexeme = lambda p: p << whitespace
skeleton_lexeme = (
    lambda p: p << whitespace_no_nl
)  # For skeleton rules to preserve newlines

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
impl = lexeme(string(":-"))
newline = lexeme(string("\n"))
question_mark = string("?")
dollar = string("$")
number = regex(r"[0-9]+")
arith_operators = ["<=", ">=", "<", "=", "+", "-", "**", "*", "/", "\\"]
arith = string_from(*arith_operators)

# Skeleton-specific punctuation (preserves newlines)
skeleton_dot = skeleton_lexeme(string("."))
skeleton_impl = skeleton_lexeme(string(":-"))

# Primitives

string_part = regex(r'[^"\\]+')

rule_name = lexeme(at >> regex(r"[A-Za-z\-0-9]+"))
rule_tokens = regex(r"[A-Za-z0-9\-\{\},:;()]+") | arith


def pattern_rule():
    pattern_variable = lexeme(question_mark >> regex(r"[a-z]+[a-z0-9]*")).map(
        PatternVariable
    )

    @generate
    def pattern_variable_collection():
        yield question_mark
        name = yield regex(r"[a-z]+[a-z0-9]*")

        option = yield lbrack.optional()

        options = None
        if option:
            options = yield regex(r"[\.\;\:\,]+")
            options = list(set(options))
            yield rbrack

        yield string("*")

        if options:
            return PatternVariableCollection(name, options)
        else:
            return PatternVariableCollection(name)

    pattern_rule_tokens = (
        lexeme(rule_tokens) | lexeme(pattern_variable_collection) | pattern_variable
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

    # Non-lexeme bracket versions to preserve spacing in skeleton rules
    skeleton_lbrack = string("[")
    skeleton_rbrack = string("]")

    # Extension that is added after the variable is expanded in the rewriting
    variable_extension = regex(r"[\_\']+[a-z0-9\'\_A-Z]*")

    # reference to a pattern variable, e.g. $h
    skeleton_reference_variable = seq(
        dollar >> regex(r"[a-z]+[a-z0-9]*"), variable_extension.optional("")
    ).combine(lambda var, ext: SkeletonVariable(var, ext))

    # extraction of the variables inside a match. E.g. with ?body, $body/vars is
    # expanded to the variables appearing inside whatever was matched in ?body
    skeleton_reference_variable_vars = seq(
        dollar >> regex(r"[a-z]+[a-z0-9]*") << string("/vars"),
        variable_extension.optional(""),
    ).combine(lambda var, ext: SkeletonVariableVarExpansion(var, ext))

    # numeric variable that denotes a newly generated symbol, e.g. $1
    skeleton_numeric_variable = seq(
        dollar >> regex(r"[0-9]+"), variable_extension.optional("")
    ).combine(lambda name, ext: NumberSkeletonVariable(name, ext))

    # named variable that denotes a newly generated symbol, e.g. $[val]
    skeleton_new_named_variable = seq(
        dollar >> skeleton_lbrack >> regex(r"[a-z]+[a-z0-9]*") << skeleton_rbrack,
        variable_extension.optional(""),
    ).combine(lambda name, ext: NamedSkeletonVariable(name, ext))

    skeleton_variable = (
        skeleton_new_named_variable
        | skeleton_reference_variable_vars
        | skeleton_reference_variable
        | skeleton_numeric_variable
    )

    # Capture whitespace as tokens
    space = regex(r"\s+")

    # Rule tokens with space - captures tokens interspersed with spaces
    skeleton_rule_tokens = (skeleton_variable | rule_tokens | space).at_least(1)

    skeleton_rule_head = skeleton_rule_tokens
    skeleton_rule_body = skeleton_rule_tokens

    skeleton_fact = seq(skeleton_rule_head, skeleton_dot).combine(lambda x, y: x + [y])
    skeleton_constraint = seq(skeleton_impl, skeleton_rule_body, skeleton_dot).combine(
        lambda impl, body, dot: [impl] + body + [dot]
    )
    skeleton_full_rule = (skeleton_rule_head >> skeleton_impl) + seq(
        skeleton_rule_body, skeleton_dot
    ).combine(lambda x, y: x + [y])

    _skeleton = yield (skeleton_constraint | skeleton_fact | skeleton_full_rule)

    when = yield skeleton_lexeme(string("when")).optional()
    conditions = []

    when_condition = seq(
        lexeme(string("not")).optional(), skeleton_lexeme(skeleton_variable)
    ).combine(lambda not_, var: SkeletonCondition(var, not_ is None))

    if when:
        conditions = yield seq(
            (when_condition << comma).many(), when_condition
        ).combine(lambda cs, c: cs + [c])

    return Skeleton(_skeleton, when=conditions)


@generate
def indent():
    try:
        yield string("\t") | string(" ").times(4)
    except:
        return fail("Expected indentation")


@generate
def rewriting_rule():
    name = yield whitespace >> rule_name
    pattern = yield pattern_rule()
    arrow = whitespace << string("->") >> string(" ").many()
    yield arrow

    nl = yield string("\n").optional()
    if nl:
        skeletons = yield (indent >> skeleton_rule << string("\n").optional()).at_least(
            1
        )
    else:
        skeletons = yield skeleton_rule.at_least(1)
    return RewritingRule(name, pattern, skeletons)


@dataclass
class RuleParser:

    def parse(self, rule: str) -> RewritingRule:
        return rewriting_rule.parse(rule)

    def parse_pattern(self, pattern: str):
        return pattern_rule().parse(pattern)

    def parse_skeleton(self, skeleton: str):
        return skeleton_rule.parse(skeleton)


class IndentationError(Exception):
    pass
