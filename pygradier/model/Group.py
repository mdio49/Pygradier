from abc import ABC, abstractproperty

class Group(ABC):
    """An abstract class for a group that matches a particular regular expression."""
    
    def __init__(self):
        pass
    
    def __str__(self):
        return self.name
    
    @abstractproperty
    def name(self) -> str:
        pass
        
    @abstractproperty
    def regex(self) -> str:
        pass

class GenericGroup(Group):

    def __init__(self, name, regex):
        self.__name = name
        self.__regex = regex

    @property
    def name(self):
        return self.__name
    
    @property
    def regex(self):
        return self.__regex

class KeywordGroup(Group):

    def __init__(self, name, *keywords):
        self.__name = name
        self.__keywords = keywords
    
    @property
    def name(self):
        return self.__name
    
    @property
    def regex(self):
        return '|'.join(x.replace('|', r'\|') for x in self.__keywords)

"""A group that matches anything except a whitespace."""
Generic = GenericGroup("generic", r'[^\s]+')

"""A group that matches integers."""
Integer = GenericGroup("integer", r'-?\d+')

"""A group that matches decimal numbers."""
Float = GenericGroup("float", r'\d*\.\d+')

"""A group that matches a range."""
Range = GenericGroup("range", r'-?\d+\.{2}(?:-?\d+)?|(?:-?\d+)?\.{2}-?\d+')

"""A group that matches a decimal number that can optionally be prefixed using tilde (~) or caret (^) notation."""
RelativeFloat = GenericGroup("relfloat", r'[~\^]?\d*\.?\d+|[~\^]')

"""A group that matches a decimal number that may have a literal character suffixed to the end of it."""
Number = GenericGroup("number", r'-?\d*\.?\d+[BbDdFfLlSs]?')

"""A group that matches a series of alphanumeric characters with no spaces."""
Word = GenericGroup("word", r'\w+')

"""A group that matches a string."""
String = GenericGroup("string", r'\"(?:\\.|[^\"])*\"|\'(?:\\.|[^\'])*\'')

"""A group that matches an entity selector."""
Selector = GenericGroup("selector", r'@[aeprs]')
