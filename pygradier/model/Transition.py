from enum import Enum

class Operation(Enum):

    # No operation is applied at the transition.
    NONE = 'none'
    
    # Pushes the provided state to the stack (defaults to the current state).
    PUSH = 'push'

    # Peeks at the top element of the stack. If it doesn't match the given value, then the transition cannot be used.
    PEEK = 'peek'

    # Pops the top element of the stack and transitions to that state.
    POP = 'pop'

    # Stops parsing completely.
    END = 'end'

class Transition:

    def __init__(self, group, target, operation=Operation.NONE, value=None):
        self.__group = group
        self.__target = target
        self.__operation = operation
        self.__value = value
    
    @property
    def group(self):
        return self.__group
    
    @property
    def target(self):
        return self.__target

    @property
    def operation(self):
        return self.__operation
    
    @property
    def value(self):
        return self.__value
