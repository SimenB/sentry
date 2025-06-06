import type {Query} from 'history';

import type {Category} from 'sentry/components/platformPicker';
import type {InjectedRouter} from 'sentry/types/legacyReactRouter';

import type {PlatformIntegration, PlatformKey, Project} from './project';

export enum OnboardingTaskGroup {
  GETTING_STARTED = 'getting_started',
  BEYOND_BASICS = 'beyond_basics',
}

export enum OnboardingTaskKey {
  FIRST_PROJECT = 'create_project',
  FIRST_EVENT = 'send_first_event',
  INVITE_MEMBER = 'invite_member',
  SECOND_PLATFORM = 'setup_second_platform',
  RELEASE_TRACKING = 'setup_release_tracking',
  SOURCEMAPS = 'setup_sourcemaps',
  ALERT_RULE = 'setup_alert_rules',
  FIRST_TRANSACTION = 'setup_transactions',
  REAL_TIME_NOTIFICATIONS = 'setup_real_time_notifications',
  LINK_SENTRY_TO_SOURCE_CODE = 'link_sentry_to_source_code',
  SESSION_REPLAY = 'setup_session_replay',
  /// Demo New Walkthrough Tasks
  SIDEBAR_GUIDE = 'sidebar_guide',
  ISSUE_GUIDE = 'issue_guide',
  RELEASE_GUIDE = 'release_guide',
  PERFORMANCE_GUIDE = 'performance_guide',
}

interface OnboardingTaskDescriptorBase {
  description: string;
  /**
   * Should the onboarding task currently be displayed
   */
  display: boolean;
  /**
   * Can this task be skipped?
   */
  skippable: boolean;
  task: OnboardingTaskKey;
  title: string;
  /**
   * The group that this task belongs to, e.g. basic and level up
   */
  group?: OnboardingTaskGroup;
  /**
   * Joins with this task id for server-side onboarding state.
   * This allows you to create alias for exising onboarding tasks or create multiple
   * tasks for the same server-side task.
   */
  serverTask?: string;
}

interface OnboardingTypeDescriptorWithAction extends OnboardingTaskDescriptorBase {
  action: (props: InjectedRouter) => void;
  actionType: 'action';
}

interface OnboardingTypeDescriptorWithExternal extends OnboardingTaskDescriptorBase {
  actionType: 'external';
  location: string;
}

interface OnboardingTypeDescriptorWithAppLink extends OnboardingTaskDescriptorBase {
  actionType: 'app';
  location: string | {pathname: string; query?: Query};
}

export type OnboardingTaskDescriptor =
  | OnboardingTypeDescriptorWithAction
  | OnboardingTypeDescriptorWithExternal
  | OnboardingTypeDescriptorWithAppLink;

export interface OnboardingTaskStatus {
  task: OnboardingTaskKey;
  completionSeen?: string | boolean;
  data?: Record<string, string>;
  dateCompleted?: string;
  status?: 'skipped' | 'complete';
}

interface OnboardingTaskWithAction
  extends OnboardingTaskStatus,
    OnboardingTypeDescriptorWithAction {}

interface OnboardingTaskWithExternal
  extends OnboardingTaskStatus,
    OnboardingTypeDescriptorWithExternal {}

interface OnboardingTaskWithAppLink
  extends OnboardingTaskStatus,
    OnboardingTypeDescriptorWithAppLink {}

export type OnboardingTask =
  | OnboardingTaskWithAction
  | OnboardingTaskWithExternal
  | OnboardingTaskWithAppLink;

export interface UpdatedTask extends Partial<Pick<OnboardingTask, 'status' | 'data'>> {
  task: OnboardingTask['task'];
  /**
   * Marks completion seen. This differs from the OnboardingTask
   * completionSeen type as that returns the date completion was seen.
   */
  completionSeen?: boolean;
}

export interface OnboardingSelectedSDK
  extends Pick<PlatformIntegration, 'language' | 'link' | 'name' | 'type'> {
  category: Category;
  key: PlatformKey;
}

export type OnboardingRecentCreatedProject = {
  isProjectActive: boolean | undefined;
  project: Project | undefined;
};
