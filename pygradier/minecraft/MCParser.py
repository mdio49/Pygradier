import nbt, pygradier, os, json, re
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

class Parameter(Token):

    def __init__(self, match: str, group: Group, tokens: list):
        super().__init__(match, group, tokens)
    
    def __str__(self):
        return self.get_command_string()

    def get_command_string(self):
        return self.match

class NBTToken(Token):

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
            tag = TAG_String(name, value.match[1:-1])
        elif value.group == Word:
            if value.match == 'true':
                tag = TAG_Byte(name, 1)
            elif value.match == 'false':
                tag = TAG_Byte(name, 0)
            else:
                tag = TAG_String(name, value.match)
        elif value.group.name == "ByteArrayOpen":
            tag = TAG_Byte_Array(name, [int(entry.match) for entry in value.tokens])
        elif value.group.name == "IntArrayOpen":
            tag = TAG_Int_Array(name, [int(entry.match) for entry in value.tokens])
        elif value.group.name == "LongArrayOpen":
            tag = TAG_Long_Array(name, [int(entry.match) for entry in value.tokens])
        elif value.group.name == "ArrayOpen":
            tag = TAG_List(name, None)
            for entry in value.tokens:
                if sub_token.group.name == "ArrayClose":
                    break
                tag.append(cls.__get_tag(entry))
        elif value.group.name == "CompoundOpen":
            tag = TAG_Compound(name)
            for sub_token in value.tokens:
                if sub_token.group.name == "CompoundClose":
                    break
                tag.add(cls.__get_tag(sub_token))
        return tag

class SelectorArgument(Token):

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

    def __init__(self, selector: SelectorType, args: list):
        super().__init__(selector.name, Selector, args)
        self.__selector = selector
        self.__args = []
        for token in args:
            name = token.match
            negated = token.tokens[0].group.name == "Negation"
            value = token.tokens[1] if negated else token.tokens[0]
            if token.group.name == "ScoresArgument":
                scores = {}
                for score in value.tokens[:-1]:
                    match = re.match(r'^(?P<int>-?\d+)$|(?P<low>-?\d+)?\.{0,2}(?P<high>-?\d+)?', score.tokens[0].match)
                    single = int(match.group('int')) if match.group('int') else None
                    low = int(match.group('low')) if match.group('low') else None
                    high = int(match.group('high')) if match.group('high') else None
                    scores[score.match] = single if single else (low, high)
                self.__args.append(SelectorArgument(name, scores, negated=negated))
            elif token.group.name == "NBTArgument":
                self.__args.append(SelectorArgument(name, NBTToken(value), negated=negated))
            else:
                self.__args.append(SelectorArgument(name, value, negated=negated))
    
    def __str__(self):
        return f"{self.selector.value}" + (f"[{', '.join(str(arg) for arg in self.args)}]" if len(self.args) > 0 else "")

    @property
    def args(self):
        return self.__args

    @property
    def selector(self):
        return self.__selector
    
    def get_command_string(self):
        selector_args = []
        for arg in self.args:
            operator = '=!' if arg.negated else '='
            if isinstance(arg.value, dict):
                scores = ','.join(f'{k}={self.__range_to_str(v)}' for k, v in arg.value.items())
                selector_args.append(f'{arg.name}{operator}{{{scores}}}')
            elif isinstance(arg.value, NBTToken):
                selector_args.append(f'{arg.name}{operator}{arg.value.nbt}')
            else:
                selector_args.append(f'{arg.name}{operator}{arg.value.match}')
        return self.selector.value + (f"[{','.join(selector_args)}]" if len(selector_args) > 0 else "")
    
    @staticmethod
    def __range_to_str(range_tuple):
        if isinstance(range_tuple, int):
            return range_tuple
        low, high = range_tuple
        if low and high:
            return f'{low}..{high}'
        if low:
            return f'{low}..'
        if high:
            return f'..{high}'
        return None

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
        return self.match[:self.match.index(':')]

    @property
    def name(self):
        return self.match[self.match.index(':')+1:]

    @property
    def block_states(self):
        return self.__block_states
    
    @property
    def nbt(self):
        return self.__nbt
    
    def get_command_string(self):
        block_states_str = ('[' + ','.join(f'{k}={v}' for k, v in self.block_states.items()) + ']') if len(self.block_states) > 0 else ''
        return f"{self.namespace}:{self.name}{block_states_str}{self.nbt if len(self.nbt) > 0 else ''}"

class MCParser:

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
            if token.group == Selector:
                selector = next(t for t in SelectorType if t.value == token.match)
                parameter = SelectorParameter(selector, token.tokens[:-1])
            elif token.group == NamespacedID:
                parameter = NamespacedIDParameter(token)
            else:
                parameter = Parameter(token.match, token.group, token.tokens)
            parameters.append(parameter)
        return parameters
    
    @classmethod
    def rebuild_command(cls, parameters):
        """Rebuilds the original command string given a series of parameters."""
        return ' '.join(x.get_command_string() for x in parameters)
