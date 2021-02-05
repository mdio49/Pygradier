from pygradier.model.Group import Group

class Token:

    def __init__(self, match: str, group: Group, tokens: list):
        self.__match = match
        self.__group = group
        self.__tokens = tokens.copy()
    
    def __str__(self):
        return f"{str(None) if self.group is None else self.group.name}({self.match}" + (f", [{', '.join(str(t) for t in self.tokens)}]" if len(self.tokens) > 0 else "") + ")"

    @property
    def tokens(self):
        return self.__tokens

    @property
    def match(self) -> str:
        """Gets the matched string."""
        return self.__match

    @property
    def group(self) -> Group:
        """Gets the group that matched this token."""
        return self.__group
