from typing import List

from asp_rewriting.model import (
    Skeleton,
    PatternVariable,
    PatternVariableCollection,
    SkeletonVariableVarExpansion,
)
from asp_rewriting.matcher import Bindings
from dataclasses import dataclass
from asp_rewriting.model import (
    SkeletonVariable,
    NumberSkeletonVariable,
    NamedSkeletonVariable,
)
from asp_rewriting import model


def extend_token(token: SkeletonVariable, value: str) -> str:
    # the extension is added to a function name before its arguments
    paren_pos = value.find("(")
    if paren_pos > 0:
        atom_name = value[:paren_pos]
        return atom_name + token.extension + value[paren_pos:]
    else:
        return value + token.extension


@dataclass
class RuleWriter:

    def write(self, skeleton: Skeleton, bindings: Bindings) -> str:
        """
        Gives the rewriting based on `skeleton` and the `bindings`.
        """
        result = ""

        # empty result if the 'when' condition of the skeleton is not satisfied
        if skeleton.when:
            value = bindings[skeleton.when]
            if not value:
                return ""

        for token in skeleton.tokens:

            if isinstance(token, str):
                result += token
            elif isinstance(token, (NumberSkeletonVariable, NamedSkeletonVariable)):
                value = bindings[token]
                result += extend_token(token, str(value))
            else:
                value = bindings[token]
                var = bindings.get_pattern_variable(token)

                # Write the bound value of the skeleton variable, applying its extension
                if isinstance(var, PatternVariable):
                    result += extend_token(token, str(value))
                elif isinstance(var, PatternVariableCollection):
                    # TODO: If the pattern variable that is referenced by the skeleton variable is collecting multiple atoms,
                    # the extension is applied to each individual atom in the collection
                    if token.extension != "":
                        raise NotImplementedError(
                            f"Variable extension not implemented for {type(var)}"
                        )
                    if isinstance(token, SkeletonVariableVarExpansion):
                        if isinstance(value, model.Atom):
                            result += ",".join(str(v) for v in value.variables)
                        elif isinstance(value, list):
                            result += ",".join(
                                str(v)
                                for atom in value
                                if isinstance(atom, model.Atom)
                                for v in atom.variables
                            )
                        else:
                            raise NotImplementedError(
                                f"Variable expansion not implemented for {type(value)}"
                            )
                    else:
                        assert isinstance(
                            value, list
                        ), f"Binding is of type {type(value)}"
                        assert all(isinstance(x, (model.Atom, str)) for x in value)

                        result += "".join(str(x) for x in value)
                else:
                    raise NotImplementedError(
                        f"Rewriting not implemented for {type(var)}"
                    )

        return result
