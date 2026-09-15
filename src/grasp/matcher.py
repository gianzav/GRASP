"""
Author: Gianluca Zavan
Email: gianluca.zavan@aau.at
Affiliation: AAU Klagenfurt


Generation of a custom parser based on a user-defined pattern.
"""

import collections
import itertools
from dataclasses import dataclass
from typing import Dict, List, NewType, Optional, Set

import parsy

from grasp import model
from grasp.model import NamedSkeletonVariable, NumberSkeletonVariable, SkeletonVariable
from grasp.parser import (
    RuleParser,
    arith,
    arith_operators,
    comma,
    lexeme,
    semicolon,
    whitespace,
)

VarName = NewType("VarName", str)

lparen = lexeme(parsy.string("("))
rparen = lexeme(parsy.string(")"))

variable = lexeme(parsy.regex(r"[_]*[A-Z]+[a-z0-9_']*")).map(model.Variable)
predicate_symbol = lexeme(parsy.regex(r"[_]*[a-z]+[A-Za-z0-9'_]*"))
digits = parsy.regex(r"[0-9]+").map(lambda x: model.Integer(int(x)))
term = parsy.forward_declaration()


def flatten(l: list) -> list:
    return list(itertools.chain.from_iterable(l))


@parsy.generate
def atom():
    separator = comma | semicolon
    withcomma = parsy.seq(term, separator).combine(lambda a, c: [a, c])
    arglist = parsy.seq(
        (withcomma).many().map(flatten),
        term,
    ).combine(lambda args, arg: args + [arg])

    not_ = yield lexeme(parsy.string("not").optional())
    name = yield predicate_symbol

    args = None
    openparen = yield lparen.optional()
    if openparen:
        args = yield arglist.optional()
        yield rparen

    if args:
        return model.Atom(name, args, positive=not_ is None)
    else:
        return model.Atom(name, positive=not_ is None)


type MatchValue = model.Atom | List[
    model.Term | str
] | model.Integer | model.String | model.PredicateSymbol


# avoid left-recursion: start binary expressions from a simple term
# (atom, variable or integer) and recurse on the right-hand side only.
simple_term = atom | variable | digits

binary_op = parsy.seq(lexeme(simple_term), lexeme(arith), lexeme(simple_term)).combine(
    lambda left, op, right: model.Arithmetic(op, [left, right])
)

# once the forward declaration is resolved, a term may be a binary expression
# or just a simple term
term.become(binary_op | simple_term)


@dataclass
class Match:
    variable: model.PatternVariable | model.PatternVariableCollection
    value: Optional[MatchValue] = None

    def __eq__(self, other):
        return (
            isinstance(other, Match)
            and self.variable.name == other.variable.name
            and self.value == other.value
        )

    def bind_value(self, value: MatchValue):
        return Match(self.variable, value)


class Bindings:
    def __init__(
        self,
        bindings: (
            Dict[model.PatternVariable | model.PatternVariableCollection, MatchValue]
            | None
        ) = None,
    ):
        self.counter = itertools.count()
        self._bindings = bindings if bindings else dict()
        self._names = {var.name: var for var in self._bindings}
        # bindings for fresh skeleton variables
        self._fresh_bindings: Dict[str, str] = dict()
        self._vars_keys: Dict[VarName, str] = dict()

    def _gen_fresh_key(
        self, var: NamedSkeletonVariable | NumberSkeletonVariable
    ) -> str:
        if isinstance(var, NamedSkeletonVariable):
            key = "_" + var.name + str(next(self.counter))
        else:
            key = "_new" + str(next(self.counter))
        self._vars_keys[var.name] = key
        return key

    def get_binding(self, key: VarName | SkeletonVariable) -> MatchValue | str:
        if isinstance(key, str):  # VarName
            _key = self._names[key]
            return self._bindings[_key]
        elif isinstance(key, (NamedSkeletonVariable, NumberSkeletonVariable)):
            if key.name in self._vars_keys:
                return self._fresh_bindings[self._vars_keys[key.name]]
            fresh_key = self._gen_fresh_key(key)
            self._fresh_bindings[self._vars_keys[key.name]] = fresh_key
            return self._fresh_bindings[self._vars_keys[key.name]]
        elif isinstance(key, SkeletonVariable):
            _key = self._names[key.name]
            return self._bindings[_key]
        else:
            raise TypeError(f"Can't access binding for value of type {type(key)}")

    def __getitem__(self, key) -> MatchValue | str:
        return self.get_binding(key)

    def get_pattern_variable(
        self, key: VarName | SkeletonVariable
    ) -> model.PatternVariable | model.PatternVariableCollection:
        if isinstance(key, str):
            return self._names[key]
        elif isinstance(key, SkeletonVariable):
            return self._names[key.name]
        else:
            raise TypeError(f"Can't access binding for value of type {type(key)}")


@dataclass
class RuleMatcher:
    parser: RuleParser

    def _generate_token_matcher(
        self, token: model.PatternToken, next_token: str | None = None
    ) -> parsy.Parser:
        # match full atoms unless the pattern explicitly continues with a
        # left parenthesis; in that case the pattern variable should bind only
        # the name of the atom, not the whole atom with arguments.
        if isinstance(token, model.PatternVariable):
            if next_token == "(":
                return lexeme(predicate_symbol | variable | digits)
            if isinstance(next_token, str) and next_token.startswith("("):
                return lexeme(predicate_symbol.map(model.Atom) | variable | digits)
            return lexeme(term)
        elif isinstance(token, model.PatternVariableCollection):

            over_parser = parsy.alt(*(parsy.string(o) for o in token.over))

            return lexeme(
                parsy.seq(term, over_parser.optional()).combine(
                    lambda x, y: [x] if y is None else [x, y]
                )
            )
        else:  # str
            return lexeme(parsy.string(token))

    def _generate_pattern_matcher(self, pattern: model.Pattern) -> parsy.Parser:
        tokens = list(pattern.tokens)

        def parse_from(
            stream: str,
            index: int,
            token_index: int,
            values: List[Match | str],
            bindings: Dict[str, MatchValue],
            collection_constrained: Set[str],
        ) -> parsy.Result:
            if token_index == len(tokens):
                return parsy.Result.success(index, values)

            token = tokens[token_index]
            next_token = (
                tokens[token_index + 1] if token_index + 1 < len(tokens) else None
            )

            if isinstance(token, model.PatternVariableCollection):
                item_parser = self._generate_token_matcher(token)
                collection_values: List[model.Term | str] = []
                current_index = index
                following_variables = [
                    following_token.name
                    for following_token in tokens[token_index + 1 :]
                    if isinstance(following_token, model.PatternVariable)
                ]
                has_later_collection = any(
                    isinstance(following_token, model.PatternVariableCollection)
                    for following_token in tokens[token_index + 1 :]
                )
                constrained_after_collection = collection_constrained | {
                    name
                    for name in following_variables
                    if has_later_collection and following_variables.count(name) > 1
                }

                while True:
                    match_values = collection_values.copy()
                    repeated_variable_follows = any(
                        isinstance(following_token, model.PatternVariable)
                        and following_token.name in bindings
                        for following_token in tokens[token_index + 1 :]
                    )
                    if (
                        repeated_variable_follows
                        and len(match_values) > 2
                        and isinstance(match_values[-1], str)
                    ):
                        match_values.pop()
                    match = Match(token, match_values)
                    assert match.value is not None
                    result = parse_from(
                        stream,
                        current_index,
                        token_index + 1,
                        values + [match],
                        bindings | {token.name: match.value},
                        constrained_after_collection,
                    )
                    if result.status:
                        return result

                    item_result = item_parser(stream, current_index)
                    if not item_result.status:
                        return parsy.Result.failure(
                            current_index, "a matching collection"
                        )
                    collection_values.extend(item_result.value)
                    current_index = item_result.index

            if isinstance(token, str):
                result = self._generate_token_matcher(token)(stream, index)
                if not result.status:
                    return result
                return parse_from(
                    stream,
                    result.index,
                    token_index + 1,
                    values + [result.value],
                    bindings,
                    collection_constrained,
                )

            if isinstance(next_token, str) and next_token in arith_operators:
                token_parser = lexeme(simple_term)
            else:
                token_parser = self._generate_token_matcher(
                    token, next_token if isinstance(next_token, str) else None
                )
            result = token_parser(stream, index)
            if not result.status:
                return result

            match = Match(token, result.value)
            if (
                token.name in collection_constrained
                and token.name in bindings
                and bindings[token.name] != result.value
            ):
                return parsy.Result.failure(result.index, "repeated variable")
            return parse_from(
                stream,
                result.index,
                token_index + 1,
                values + [match],
                bindings | {token.name: result.value},
                collection_constrained,
            )

        def pattern_parser(stream: str, index: int) -> parsy.Result:
            whitespace_result = whitespace(stream, index)
            return parse_from(stream, whitespace_result.index, 0, [], {}, set())

        return parsy.Parser(pattern_parser)

    def match(
        self, pattern: str | model.Pattern | model.PatternAlternative, rule: str
    ) -> List[Match | str]:
        if isinstance(pattern, str):
            alternatives: model.PatternAlternative = self.parser.parse_pattern(pattern)
            matcher = parsy.alt(
                *(self._generate_pattern_matcher(p) for p in alternatives)
            )
            variables = set.union(*(p.variables for p in alternatives))
        elif isinstance(pattern, model.PatternAlternative):
            matcher = parsy.alt(*(self._generate_pattern_matcher(p) for p in pattern))
            variables = set.union(*(p.variables for p in pattern))
        else:  # model.Pattern
            assert isinstance(pattern, model.Pattern)
            matcher = self._generate_pattern_matcher(pattern)
            variables = pattern.variables

        matches = matcher.parse(rule)
        self._validate_bindings(matches, variables)
        return matches

    def _validate_bindings(
        self,
        matches: List[Match | str],
        variables: Set[model.PatternVariable | model.PatternVariableCollection],
    ) -> Dict[model.PatternVariable | model.PatternVariableCollection, MatchValue]:
        bindings: Dict[
            model.PatternVariable | model.PatternVariableCollection, MatchValue
        ] = {}
        variable_matches = [m for m in matches if not isinstance(m, str)]

        for match in variable_matches:
            variable, value = match.variable, match.value

            if value is None:
                raise BindingError(f"None was matched to {variable}")

            if variable in bindings and bindings[variable] != value:
                raise BindingError(
                    f"Variable {str(variable)} can't match on {bindings[variable]} and {value}"
                )

            bindings[variable] = value

        for var in variables:
            # variable was mentioned in one of the pattern alternatives but got no match
            if var not in bindings:
                bindings[var] = model.String("")

        return bindings

    def get_bindings(self, pattern: model.PatternAlternative, rule: str) -> Bindings:
        # extract all the variables appearing in the alternatives to handle unbound variables later
        variables = set.union(*(p.variables for p in pattern))
        matches = self.match(pattern, rule)
        bindings = self._validate_bindings(matches, variables)
        return Bindings(bindings)


class BindingError(Exception):
    def __init__(self, msg):
        super().__init__(msg)
