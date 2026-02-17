from asp_rewriting.parser import RuleParser
from asp_rewriting.model import *

rule = """\
@rule-name ?a :- ?b, ?body*. -> 
    p :- $a.
    $[new] :- $b, $1.
    p($body/vars) :- a.
    {$[choice]} :- p,q,r. when $choice
"""
parser = RuleParser()

print(parser.parse(rule))
