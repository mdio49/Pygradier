from pygradier.model.Model import Model
from pygradier.model.State import State
from pygradier.model.Transition import Transition
from pygradier.model.Transition import Operation
from pygradier.model.Group import GenericGroup
from pygradier.Token import Token

class ParserError(Exception):

    def __init__(self, msg, line, pos):
        super().__init__(msg + f" HERE --> {line[pos:pos+10]} ...")

class InvalidTokenError(ParserError):

    def __init__(self, line, pos):
        super().__init__(f"Could not match line to an appropriate group", line, pos)

class NonExistentTransitionError(ParserError):

    def __init__(self, line, pos):
        super().__init__(f"No transition exists for the given match", line, pos)

class IncompleteParsingError(ParserError):

    def __init__(self, line, pos):
        super().__init__(f"Unexpected end of parsing", line, pos)

class EndOfLineError(ParserError):

    def __init__(self, line, pos):
        super().__init__(f"Unexpected end of line while parsing", line, pos)

class Parser:

    def __init__(self, model: Model):
        self.__model = model

    @property
    def model(self):
        return self.__model
    
    def tokenize(self, line: str):
        state = self.model.start
        stack = []
        tokens = []
        
        finished = False
        while not finished:
            # Match the state's pattern at the current position in the line.
            pattern = state.build_regex()
            match = pattern.match(line)
            if not match:
                raise InvalidTokenError(line, 0)
            
            # Advance the search forward based on the length of the match.
            length = match.end()
            line = line[length:]

            # Get the group that was matched.
            group = state.get_matched_group(match)
            assert group != None

            # Add the match as a token.
            text = match.group(group.name)
            token = Token(text, group, [])
            if state.tokenize:
                tokens.append(token)

            # Get the next state that this state transitions to given that the particular group was matched.
            transition = state.get_transition(group, stack)
            if not transition:
                raise NonExistentTransitionError(line, 0)
            
            if transition.operation == Operation.PUSH:
                stack.append((transition.value, token, tokens))
                tokens = []
            elif transition.operation == Operation.POP:
                subtokens = tokens
                state, token, tokens = stack.pop()
                token.tokens.extend(subtokens)
            elif transition.operation == Operation.END:
                finished = True
            
            state = transition.target
        
        if len(stack) > 0:
            raise EndOfLineError(line, 0)

        if len(line) > 0:
            raise IncompleteParsingError(line, 0)

        return tokens
