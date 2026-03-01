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
import copy


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
                        # TODO: If the pattern variable that is referenced by the skeleton variable is collecting multiple atoms,
                        # the extension is applied to each individual atom in the collection

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
