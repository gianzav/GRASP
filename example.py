from grasp.parser import RuleParser
from grasp.model import *

rule = """\
@rule-name ?a :- ?b, ?body*. -> 
    p :- $a.
    $[new] :- $b, $1.
    p($body/vars) :- a.
    {$[choice]} :- p,q,r. when $choice
"""
parser = RuleParser()

print(parser.parse(rule))
