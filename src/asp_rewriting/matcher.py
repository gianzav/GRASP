"""
Author: Gianluca Zavan
Email: gianluca.zavan@aau.at
Affiliation: AAU Klagenfurt


Generation of a custom parser based on a user-defined pattern.
"""

import parsy
from asp_rewriting import model
from dataclasses import dataclass
from typing import Dict
from asp_rewriting.parser import whitespace, RuleParser, lexeme, comma, semicolon
import itertools


type VarName = str
type Symbol = str
type Bindings = Dict[VarName, Symbol]

lparen = lexeme(parsy.string("("))
rparen = lexeme(parsy.string(")"))

variable = lexeme(parsy.regex(r"[_A-Z]+[A-Za-z0-9_']*"))
predicate_symbol = lexeme(parsy.regex(r"[a-z]+[A-Za-z0-9'_]*"))
digits = parsy.regex(r"[0-9]+")


@parsy.generate
def atom():
    parens = lambda p: parsy.seq(lparen, p, rparen).combine(
        lambda l, a, r: [l] + a + [r]
    )

    arglist = parsy.seq(
        ((variable | atom) + (comma | semicolon)).many(), (variable | atom)
    ).combine(lambda args, arg: args + [arg])

    name = yield predicate_symbol

    args = None
    args = yield parens(arglist).optional()

    if args:
        return name + "".join(args)
    else:
        return name


def generate_token_matcher(token: model.PatternToken) -> parsy.Parser:
    # match full atoms
    if isinstance(token, model.PatternVariable):
        return lexeme(atom | digits)
    elif isinstance(token, model.PatternVariableCollection):

        over_parser = parsy.alt(*(parsy.string(o) for o in token.over))

        return lexeme(lexeme(atom | digits) + over_parser.optional("")).concat()
    else:  # str
        return lexeme(parsy.string(token))


def generate_pattern_matcher(pattern: model.Pattern) -> parsy.Parser:
    parser = whitespace.map(lambda x: [])

    skip = False
    for token, next_token in itertools.zip_longest(
        pattern.tokens, list(pattern.tokens)[1:]
    ):
        # match eagerly all the atoms up to the next token
        if (
            isinstance(token, model.PatternVariableCollection)
            and next_token is not None
        ):
            this = generate_token_matcher(token)
            next_ = generate_token_matcher(next_token)

            # parse partially until the next parser is triggered
            parser += this.until(next_).concat().map(lambda x: [x])
        else:
            parser += generate_token_matcher(token).map(lambda x: [x])
    return parser


@dataclass
class RuleMatcher:
    parser: RuleParser

    def match(self, pattern: str, rule: str):
        parsed: model.Pattern = self.parser.parse_pattern(pattern)
        matcher = generate_pattern_matcher(parsed)
        return matcher.parse(rule)
