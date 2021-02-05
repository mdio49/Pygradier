import re
from pygradier.model.Transition import Operation
from pygradier.model.Transition import Transition

class State:

    def __init__(self, groups: list, transitions: list, tokenize=True):
        self.__groups = groups.copy()
        self.__transitions = transitions.copy()
        self.__tokenize = tokenize
    
    @property
    def groups(self):
        """A list of groups that are matched at this state (in order)."""
        return self.__groups
    
    @property
    def transitions(self):
        """A set of transitions to other states based on the matched group."""
        return self.__transitions

    @property
    def tokenize(self):
        """Indicates whether the state should generate tokens."""
        return self.__tokenize
    
    def build_regex(self):
        """Builds the regular expression that fully matches this state."""
        pattern = f"({')|('.join(f'?P<{g.name}>{g.regex}' for g in self.groups)})"
        return re.compile(pattern)

    def get_matched_group(self, match):
        return next((g for g in self.groups if match.group(g.name) is not None), None)
    
    def get_transition(self, group, stack):
        for t in self.transitions:
            if t.operation == Operation.PEEK and stack[-1][0] != t.value:
                continue
            if t.group == group or t.group is None:
                return Transition(group, stack[-1][0], operation=t.operation) if t.operation == Operation.POP else t
        return Transition(group, self)
