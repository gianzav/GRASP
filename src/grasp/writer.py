from typing import List

from grasp.model import (
    Skeleton,
    PatternVariable,
    PatternVariableCollection,
    SkeletonVariableVarExpansion,
)
from grasp.matcher import Bindings
from dataclasses import dataclass
from grasp.model import (
    SkeletonVariable,
    NumberSkeletonVariable,
    NamedSkeletonVariable,
)
from grasp import model
import copy


def extend_token(token: SkeletonVariable, value: str) -> str:
    # the extension is added to a function name before its arguments
    paren_pos = value.find("(")
    if paren_pos > 0:
        atom_name = value[:paren_pos]
        return atom_name + token.extension + value[paren_pos:]
    else:
        return value + token.extension


# TODO: refactor this ugly ugly function
def condition_satisfied(condition: model.SkeletonCondition, bindings: Bindings) -> bool:
    value = bindings[condition.variable]

    if not value or value == model.String(""):
        return not condition._positive

    if isinstance(condition.variable, SkeletonVariableVarExpansion):
        if isinstance(value, list):
            no_variable_in_atoms = all(
                len(atom.variables) == 0
                for atom in value
                if isinstance(atom, model.Atom)
            )
            no_element_is_variable = all(
                not isinstance(x, model.Variable) for x in value
            )

            if no_variable_in_atoms and no_element_is_variable and condition._positive:
                return False
        else:
            has_no_variables = (
                isinstance(value, model.Atom) and len(value.variables) == 0
            )
            is_not_variable = not isinstance(value, model.Variable)

            if has_no_variables and is_not_variable and condition._positive:
                return False
    return True


def when_satisfied(
    conditions: List[model.SkeletonCondition], bindings: Bindings, rule_name=""
) -> bool:
    try:
        return all(condition_satisfied(condition, bindings) for condition in conditions)
    except KeyError as e:
        raise UnboundVariableError(
            f"Variable {str(e.args[0])} unbound in rule '{rule_name}'"
        )


def remove_trailing_separators(s: str):
    return s.rstrip(" ,:;")


class UnboundVariableError(Exception):
    pass


@dataclass
class RuleWriter:

    def write(self, skeleton: Skeleton, bindings: Bindings, rule_name="") -> str:
        """
        Gives the rewriting based on `skeleton` and the `bindings`.
        """
        result = ""
        last_was_empty = False

        # empty result if the 'when' condition of the skeleton is not satisfied
        if not when_satisfied(skeleton.when, bindings, rule_name):
            return ""

        for token in skeleton.tokens:
            if isinstance(token, str):
                separators = {",", ";", ":", " "}
                if last_was_empty and token in separators:
                    # When a variable expanded to empty, we removed any trailing
                    # separators from the current result. If a separator follows
                    # the empty variable in the tokens, append it only when it
                    # makes sense:
                    # - skip if result already ends with a separator
                    # - skip if result ends with ':-' (don't insert comma after ':-')
                    if result.endswith(":-"):
                        pass
                    elif result and result[-1] in separators:
                        pass
                    else:
                        result += token
                        last_was_empty = False
                else:
                    # Ensure a space after ':-' before word tokens (not punctuation)
                    if result.endswith(":-") and token not in {",", ";", ":", " ", "."}:
                        result += " "
                    result += token
                    last_was_empty = False
            elif isinstance(token, (NumberSkeletonVariable, NamedSkeletonVariable)):
                try:
                    value = bindings[token]
                except KeyError:
                    raise UnboundVariableError(
                        f"Variable {str(token)} unbound in rule '{rule_name}'"
                    )
                result += extend_token(token, str(value))
            else:
                try:
                    value = bindings[token]
                except KeyError:
                    raise UnboundVariableError(
                        f"Variable {str(token)} unbound in rule '{rule_name}'"
                    )
                var = bindings.get_pattern_variable(token)

                # empty string binding because variable was present in pattern alternatives but was not matched against anything
                # or empty list binding because PatternVariableCollection matched against nothing
                if bindings[token] == model.String("") or bindings[token] == []:
                    # then any separator present before the "empty match" should be removed since nothing will be generated
                    result = remove_trailing_separators(result)
                    last_was_empty = True
                    continue
                else:
                    last_was_empty = False

                match (token, var):
                    case (SkeletonVariableVarExpansion(), PatternVariable()):
                        if isinstance(value, model.Atom):
                            result += ",".join(str(v) for v in value.variables)
                        elif isinstance(value, model.Variable):
                            result += str(value)
                        else:
                            raise NotImplementedError(
                                f"Variable extension not implemented for {type(value)}"
                            )
                    case (SkeletonVariableVarExpansion(), PatternVariableCollection()):
                        if isinstance(value, list):
                            result += ",".join(
                                extend_token(token, str(v))
                                for atom in value
                                if isinstance(atom, model.Atom)
                                for v in atom.variables
                            )
                        else:
                            raise NotImplementedError(
                                f"Variable expansion not implemented for {type(value)}"
                            )
                    case (SkeletonVariable(), PatternVariableCollection()):
                        # if token.extension != "":
                        #     raise NotImplementedError(
                        #         f"Variable extension not implemented for {type(var)}"
                        #     )

                        assert isinstance(
                            value, list
                        ), f"Binding is of type {type(value)}"
                        assert all(isinstance(x, (model.Atom, str)) for x in value)

                        extended = []
                        for t in value:
                            if isinstance(t, model.Term):
                                e = copy.deepcopy(t)
                                e.name = extend_token(token, e.name)
                                extended.append(e)
                            else:
                                extended.append(t)

                        result += "".join(str(e) for e in extended)
                    case (_, PatternVariable()):
                        # Write the bound value of the skeleton variable, applying its extension
                        result += extend_token(token, str(value))
                    case _:
                        raise NotImplementedError(
                            f"Rewriting not implemented for {type(var)}"
                        )

        return result
