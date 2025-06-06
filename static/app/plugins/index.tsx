import BasePlugin from 'sentry/plugins/basePlugin';
import {DefaultIssuePlugin} from 'sentry/plugins/defaultIssuePlugin';
import Registry from 'sentry/plugins/registry';

import SessionStackContextType from './sessionstack/contexts/sessionstack';
import Jira from './jira';
import SessionStackPlugin from './sessionstack';

const contexts: Record<string, React.ElementType> = {};
const registry = new Registry();

// Register legacy plugins

// Sessionstack
registry.add('sessionstack', SessionStackPlugin);
contexts.sessionstack = SessionStackContextType;

// Jira
registry.add('jira', Jira);

const add: typeof registry.add = registry.add.bind(registry);
const get: typeof registry.get = registry.get.bind(registry);
const isLoaded: typeof registry.isLoaded = registry.isLoaded.bind(registry);
const load: typeof registry.load = registry.load.bind(registry);

const plugins = {
  BasePlugin,
  DefaultIssuePlugin,

  add,
  addContext: function (id: string, component: React.ElementType) {
    contexts[id] = component;
  },
  contexts,
  get,
  isLoaded,
  load,
};

export default plugins;
