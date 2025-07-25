from sentry.utils.registry import Registry
from sentry.workflow_engine.types import ActionHandler, DataConditionHandler, DataSourceTypeHandler

data_source_type_registry = Registry[type[DataSourceTypeHandler]]()
condition_handler_registry = Registry[type[DataConditionHandler]](enable_reverse_lookup=False)
action_handler_registry = Registry[type[ActionHandler]](enable_reverse_lookup=False)
