from pygradier.model.Group import GenericGroup
from pygradier.model.State import State
from pygradier.model.Transition import Transition
from pygradier.model.Transition import Operation
from pygradier.model.groups import *

PREDEFINED_GROUPS = {
    "Generic": Generic,
    "Integer": Integer,
    "Float": Float,
    "Range": Range,
    "Interval": Interval,
    "RelativeFloat": RelativeFloat,
    "Number": Number,
    "Word": Word,
    "String": String,
    "Selector": Selector,
    "NamespacedID": NamespacedID
}

class Model:

    def __init__(self, regions: dict, start: State):
        self.__regions = regions
        self.__start = start
    
    @property
    def regions(self) -> dict:
        return self.__regions
    
    @property
    def start(self) -> State:
        return self.__start

    @classmethod
    def from_dict(cls, data, groups=PREDEFINED_GROUPS):
        regions = data['regions']
        templates = data.get('templates', {})
        parsed_regions = {}
        
        start_region = data['start']['region']
        start_state = data['start']['state']
        
        cls.__load_group_defs(data, groups)
        cls.__load_templates(data, groups)
        cls.__load_state(start_region, start_state, groups, regions, parsed_regions, templates)

        return cls(parsed_regions, parsed_regions[start_region][start_state])

    @classmethod
    def __load_group_defs(cls, data, groups):
        if 'group_defs' in data:
            for group in data['group_defs']:
                name = group['name']
                groups[name] = GenericGroup(name, group['regex'])
    
    @classmethod
    def __load_templates(cls, data, templates):
        if 'templates' in data:
            for key, template in data['templates'].items():
                templates[key] = template

    @classmethod
    def __load_state(cls, region: str, state: str, groups: dict, regions: dict, parsed_regions: dict, templates: dict):
        original_groups = groups.copy()
        original_templates = templates.copy()
        
        # Load the region data.
        region_data = regions[region]
        cls.__load_group_defs(region_data, groups)
        cls.__load_templates(region_data, templates)
        if region not in parsed_regions:
            parsed_regions[region] = {}

        # Load the state data.
        state_data = region_data['states'][state]
        if 'group_defs' not in state_data:
            state_data['group_defs'] = []
        if 'groups' not in state_data:
            state_data['groups'] = []
        if 'transitions' not in state_data:
            state_data['transitions'] = []
        if 'template' in state_data:
            template = templates[state_data['template']]
            cls.__load_group_defs(template, groups)
            state_data['groups'].extend(template.get('groups', []))
            state_data['transitions'].extend(template.get('transitions', []))
            if 'tokenize' not in state_data and 'tokenize' in template:
                state_data['tokenize'] = template['tokenize']
        cls.__load_group_defs(state_data, groups)
        ordered_groups = [groups[x] for x in state_data['groups']]
        tokenize = state_data.get('tokenize', True)
        parsed_regions[region][state] = State(ordered_groups, [], tokenize=tokenize)

        # Handle each transition.
        for transition in state_data['transitions']:
            # Get the group that matches this transition.
            group = groups[transition['group']] if 'group' in transition else None
            
            # Get the region that the target state lies in.
            target_region = cls.__resolve_region_name(transition, region)

            # Get the target state.
            target = None
            target_state = transition.get('target', None)
            if target_state:
                cls.__resolve_state(target_region, target_state, original_groups, regions, parsed_regions, original_templates)
                target = parsed_regions[target_region].get(target_state, None)

            operation = next(x for x in Operation if x.value == transition.get('operation', 'none'))
            value = parsed_regions[region][state]
            value_data = transition.get('value', {})
            if len(value_data) > 0:
                value_region = cls.__resolve_region_name(value_data, region)
                value_state = value_data['state']
                cls.__resolve_state(value_region, value_state, original_groups, regions, parsed_regions, original_templates)
                value = parsed_regions[value_region][value_state]

            parsed_regions[region][state].transitions.append(Transition(group, target, operation=operation, value=value))
    
    @classmethod
    def __resolve_region_name(cls, data: dict, this_region: str):
        region = data.get('region', 'this')
        if region == 'this':
            region = this_region
        return region

    @classmethod
    def __resolve_state(cls, region: str, state: str, groups: dict, regions: dict, parsed_regions: dict, templates: dict):
        if region not in parsed_regions or state not in parsed_regions[region]:
                cls.__load_state(region, state, groups, regions, parsed_regions, templates)
