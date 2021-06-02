import nbt, pygradier, os, json, re, codecs
from abc import ABC, abstractproperty
from enum import Enum
from pygradier.model.groups import *
from pygradier.model.Group import Group
from pygradier.model.Model import Model
from pygradier.Parser import Parser
from pygradier.Token import Token
from nbt.tags import *

PARSER = None
with open(os.path.join(os.path.dirname(__file__), 'mcparser.json'), 'r') as file:
    data = json.load(file)
    model = Model.from_dict(data)
    PARSER = Parser(model)

class SelectorType(Enum):
    ALL_PLAYERS = '@a'
    ALL_ENTITIES = '@e'
    NEAREST_PLAYER = '@p'
    RANDOM_PLAYER = '@r'
    EXECUTOR = '@s'

class TAG_Boolean(TAG_Byte):

    def __init__(self, name: str, value: bool):
        super().__init__(name, 1 if value else 0)
    
    def __str__(self):
        return 'false' if self.value == 0 else 'true'

    def set_boolean_value(self, value: bool):
        self.value = 1 if value else 0

class TAG_GenericList(nbt.NBTTag):

    def __init__(self, name: str):
        super().__init__(name, None)
        self.__tags = []
    
    def __str__(self):
        return '[' + ','.join(f'{tag}' for tag in self.tags) + ']'

    @property
    def tags(self):
        return self.__tags
    
    @property
    def value(self):
        return self
    
    def validate(self, value):
        pass

    @classmethod
    def get_id(cls):
        return None
    
    def payload(self):
        raise Exception("Generic list tags cannot be written to an NBT file.")
    
    @classmethod
    def load(cls, name, fp):
        pass

class Parameter(Token):
    """A base class for a token that serves as a command parameter that can be reconstructed into a command string."""
    
    def __init__(self, match: str, group: Group, tokens: list):
        super().__init__(match, group, tokens)
    
    def __str__(self):
        return self.get_command_string()

    def get_command_string(self):
        return self.match

class GenericParameter(Parameter):
    """A generic paramater that contains only a single keyword."""

    def __init__(self, keyword: str):
        super().__init__(keyword, Generic, [])

class RawToken(Token):
    """A raw token whose string conversion method produces its match only."""

    def __init__(self, token: Token):
        super().__init__(token.match, token.group, token.tokens)
    
    def __str__(self):
        return self.match

class BooleanToken(Token):
    """A token that contains a boolean value."""

    def __init__(self, token: Token):
        super().__init__(token.match, token.group, token.tokens)
        self.__value = True if self.match.lower() == 'true' else False
    
    def __str__(self):
        return 'true' if self.value else 'false'
    
    @property
    def value(self):
        return self.__value

class RangeToken(Token):
    """A token that contains an integer range."""

    def __init__(self, token: Token):
        super().__init__(token.match, token.group, token.tokens)
        match = re.match(r'^(?P<int>-?\d+)$|(?P<low>-?\d+)?\.{0,2}(?P<high>-?\d+)?', self.match)
        self.__value = int(match.group('int')) if match.group('int') else None
        self.__low = int(match.group('low')) if match.group('low') else None
        self.__high = int(match.group('high')) if match.group('high') else None
    
    def __str__(self):
        if self.is_integer():
            return str(self.value)
        if self.low is not None and self.high is not None:
            return f'{self.low}..{self.high}'
        if self.low is not None:
            return f'{self.low}..'
        if self.high is not None:
            return f'..{self.high}'
        return None
    
    def is_integer(self):
        """Determines whether the range is a single value."""
        return self.value is not None

    @property
    def value(self):
        """The single integer value that this range takes."""
        return self.__value

    @property
    def low(self):
        """The low end of this range (or None for negative infinity)."""
        return self.__low
    
    @property
    def high(self):
        """The high end of this range (or None for positive infinity)."""
        return self.__high

class NBTToken(Token):
    """A token that contains NBT data."""

    def __init__(self, token: Token):
        super().__init__("", token.group, [token])
        self.__root = self.__get_tag(Token("", None, [token]))
    
    def __str__(self):
        return str(self.nbt)
    
    @property
    def nbt(self):
        return self.__root

    @classmethod
    def __get_tag(cls, token):
        tag = None
        name = token.match
        value = token.tokens[0]
        if value.group == Number:
            literal = value.match[-1]
            if literal.lower() == 'b':
                tag = TAG_Byte(name, int(value.match[:-1]))
            elif literal.lower() == 'd':
                tag = TAG_Double(name, float(value.match[:-1]))
            elif literal.lower() == 'f':
                tag = TAG_Float(name, float(value.match[:-1]))
            elif literal.lower() == 'l':
                tag = TAG_Long(name, int(value.match[:-1]))
            elif literal.lower() == 's':
                tag = TAG_Short(name, int(value.match[:-1]))
            elif '.' in value.match:
                tag = TAG_Double(name, float(value.match))
            else:
                tag = TAG_Int(name, int(value.match))
        elif value.group == String:
            tag = TAG_String(name, codecs.decode(value.match[1:-1], 'unicode_escape'))
        elif value.group == Word:
            tag = TAG_String(name, value.match)
        elif value.group.name == "Boolean":
            tag = TAG_Boolean(name, True if value.match == 'true' else False)
        elif value.group.name == "ByteArrayOpen":
            tag = TAG_Byte_Array(name, [int(entry.match) for entry in value.tokens[:-1]])
        elif value.group.name == "IntArrayOpen":
            tag = TAG_Int_Array(name, [int(entry.match) for entry in value.tokens[:-1]])
        elif value.group.name == "LongArrayOpen":
            tag = TAG_Long_Array(name, [int(entry.match) for entry in value.tokens[:-1]])
        elif value.group.name == "ListOpen":
            generic_list = TAG_GenericList(name)
            use_generic_list = False
            list_type = None
            for entry in value.tokens:
                if entry.group.name == "ListClose":
                    break
                entry_tag = cls.__get_tag(entry)
                generic_list.tags.append(entry_tag)
                if list_type is None:
                    list_type = type(entry_tag)
                elif not isinstance(entry_tag, list_type):
                    use_generic_list = True
            if not use_generic_list:
                tag = TAG_List(name, list_type)
                tag.extend(generic_list.tags)
            else:
                tag = generic_list
        elif value.group.name == "CompoundOpen":
            tag = TAG_Compound(name)
            for sub_token in value.tokens:
                if sub_token.group.name == "CompoundClose":
                    break
                tag.add(cls.__get_tag(sub_token))
        return tag

class BlockStatesToken(Token):
    """A token that contains a key-value mapping of block states."""

    def __init__(self, token: Token):
        super().__init__(token.match, token.group, token.tokens)
        self.__states = {}
        for subtoken in token.tokens:
            if subtoken.group.name == 'BlockStatesEnd':
                break
            self.__states[subtoken.match] = subtoken.tokens[0].match
    
    def __str__(self):
        return ('[' + ','.join(f'{k}={v}' for k, v in self.states.items()) + ']') if len(self.states) > 0 else ''

    @property
    def states(self):
        return self.__states

class ListIndexToken(Token):
    """A token that contains a list index, the index being another token."""

    def __init__(self, index: Token):
        super().__init__("", None, [index])
        self.__index = index
    
    def __str__(self):
        return f'[{self.index}]'

    @property
    def index(self):
        return self.__index

class DictionaryToken(Token, ABC):
    """An abstract class for a token that contains a dictionary of key-value pairs."""

    def __init__(self, token: Token):
        super().__init__(token.match, token.group, token.tokens)
    
    def __str__(self):
        return '{' + ','.join(f'{k}={v}' for k, v in self.items.items()) + '}'

    @abstractproperty
    def items(self):
        pass

class ScoresToken(DictionaryToken):
    """A token that contains a mapping of scoreboard objectives to integer ranges."""

    def __init__(self, token):
        super().__init__(token)
        self.__scores = {}
        for score in token.tokens:
            if score.group.name == 'ScoresClose':
                break
            self.__scores[score.match] = RangeToken(score.tokens[0])
    
    @property
    def items(self):
        return self.__scores

class CriteriaToken(DictionaryToken):
    """A token that contains a mapping of advancement criteria to a boolean value."""

    def __init__(self, token):
        super().__init__(token)
        self.__criteria = {}
        for adv in token.tokens:
            if adv.group.name == 'CriteriaClose':
                break
            self.__criteria[adv.match] = BooleanToken(adv.tokens[0])

    @property
    def items(self):
        return self.__criteria

class AdvancementsToken(DictionaryToken):
    """A token that contains a mapping of advancements to either a boolean value or a `CriteriaToken`."""

    def __init__(self, token):
        super().__init__(token)
        self.__advancements = {}
        for adv in token.tokens:
            if adv.group.name == 'AdvancementsClose':
                break
            name = adv.match
            value = adv.tokens[0]
            if value.group.name == 'CriteriaOpen':
                self.__advancements[name] = CriteriaToken(value)
            else:
                self.__advancements[name] = BooleanToken(value)

    @property
    def items(self):
        return self.__advancements

class SelectorArgument(Token):
    """A token that represents a selector argument (a name with a corresponding value)."""

    def __init__(self, name: str, value: Token, negated=False):
        super().__init__(name, SelectorArgument, [value])
        self.__value = value
        self.__negated = negated
    
    def __str__(self):
        return f"{self.name} {'!' if self.negated else ''}= {self.value}"

    @property
    def name(self):
        return self.match
    
    @property
    def value(self):
        return self.__value
    
    @property
    def negated(self):
        return self.__negated

class SelectorParameter(Parameter):
    """A selector parameter, containing a particular type of entity selector with an optional list of arguments."""

    def __init__(self, selector: SelectorType, args: list):
        super().__init__(selector.name, Selector, args)
        self.__selector = selector
        self.__args = []
        for token in args:
            name = token.match
            negated = token.tokens[0].group.name == "Negation"
            value = token.tokens[1] if negated else token.tokens[0]
            if token.group.name == "ScoresArgument":
                self.__args.append(SelectorArgument(name, ScoresToken(value), negated=negated))
            elif token.group.name == "NBTArgument":
                self.__args.append(SelectorArgument(name, NBTToken(value), negated=negated))
            elif token.group.name == "AdvancementsArgument":
                self.__args.append(SelectorArgument(name, AdvancementsToken(value), negated=negated))
            else:
                self.__args.append(SelectorArgument(name, RawToken(value), negated=negated))
    
    def __str__(self):
        return f"{self.selector.value}" + (f"[{', '.join(str(arg) for arg in self.args)}]" if len(self.args) > 0 else "")

    @property
    def selector(self):
        return self.__selector
    
    @property
    def args(self):
        return self.__args
    
    def get_command_string(self):
        selector_args = []
        for arg in self.args:
            operator = '=!' if arg.negated else '='
            selector_args.append(f'{arg.name}{operator}{arg.value}')
        return self.selector.value + (f"[{','.join(selector_args)}]" if len(selector_args) > 0 else "")

class NamespacedIDParameter(Parameter):

    def __init__(self, token: Token):
        super().__init__(token.match, NamespacedID, token.tokens)
        self.__block_states = {}
        self.__nbt = TAG_Compound("")
        for subtoken in token.tokens:
            if subtoken.group.name == 'BlockStatesOpen':
                for state in subtoken.tokens:
                    if state.group.name == 'BlockStatesEnd':
                        break
                    self.__block_states[state.match] = state.tokens[0].match
            if subtoken.group.name == 'CompoundOpen':
                self.__nbt = NBTToken(subtoken).nbt

    @property
    def namespace(self):
        return self.match[:self.match.index(':')] if ':' in self.match else None

    @property
    def name(self):
        return self.match[self.match.index(':')+1:] if ':' in self.match else self.match

    @property
    def block_states(self):
        return self.__block_states
    
    @property
    def nbt(self):
        return self.__nbt
    
    def get_command_string(self):
        block_states_str = ('[' + ','.join(f'{k}={v}' for k, v in self.block_states.items()) + ']') if len(self.block_states) > 0 else ''
        return f"{(self.namespace + ':') if self.namespace else ''}{self.name}{block_states_str}{self.nbt if len(self.nbt) > 0 else ''}"

class Comment(Parameter):
    """A parameter that defines a comment."""

    def __init__(self, token: Token):
        super().__init__(token.match, token.group, [])

    def __str__(self):
        return "Comment(" + self.match + ")"

    def get_command_string(self):
        return "# " + self.match 

class HybridParameter(Parameter):
    """A parameter that is combined from multiple tokens where the parameter's type is ambiguous."""

    def __init__(self, token: Token):
        super().__init__(token.match, token.group, [self.__parse_token(t) for t in token.tokens])
    
    def get_command_string(self):
        return ''.join(str(token) for token in self.tokens)
        
    @classmethod
    def __parse_token(cls, token):
        if token.group.name == 'CompoundOpen' or token.group.name == 'ListOpen':
            return NBTToken(token)
        elif token.group.name == 'BlockStatesOpen':
            return BlockStatesToken(token)
        elif token.group.name == 'ListIndexOpen':
            return ListIndexToken(cls.__parse_token(token.tokens[0]))
        return RawToken(token)

class MCParser:
    """A static class that parses commands in vanilla Minecraft."""

    def __init__(self):
        pass

    @staticmethod
    def get_parser() -> pygradier.Parser:
        return PARSER

    @classmethod
    def tokenize(cls, line):
        """Tokenizes a command into a list of raw tokens."""
        return cls.get_parser().tokenize(line)
    
    @classmethod
    def parse(cls, line):
        """Parses a command into a list of parameterized tokens."""
        tokens = cls.tokenize(line)
        return cls.parse_tokens(tokens)
    
    @classmethod
    def parse_tokens(cls, tokens):
        """Parses a series of raw tokens into a series of parameters."""
        parameters = []
        for token in tokens:
            parameter = None
            if token.group.name == 'EOL':
                break
            elif token.group.name == 'SelectorParameter':
                selector = next(t for t in SelectorType if t.value == token.match)
                parameter = SelectorParameter(selector, token.tokens[:-1])
            elif token.group.name == 'HybridParameter':
                parameter = HybridParameter(token)
            elif token.group.name == 'Comment':
                parameter = Comment(token)
            elif token.group.name == 'Keyword':
                parameter = GenericParameter(token.match)
            else:
                parameter = Parameter(token.match, token.group, token.tokens)
            parameters.append(parameter)
        return parameters
    
    @classmethod
    def rebuild_command(cls, parameters):
        """Rebuilds the original command string given a series of parameters."""
        return ' '.join(x.get_command_string() for x in parameters)
