import {Fragment, useState} from 'react';
import styled from '@emotion/styled';
import {PlatformIcon, platforms} from 'platformicons';

import {Input} from 'sentry/components/core/input';
import {Tooltip} from 'sentry/components/core/tooltip';
import {Sticky} from 'sentry/components/sticky';
import * as Icons from 'sentry/icons';
import {PluginIcon, type PluginIconProps} from 'sentry/plugins/components/pluginIcon';
import * as Storybook from 'sentry/stories';
import {space} from 'sentry/styles/space';
import {
  IdentityIcon,
  type IdentityIconProps,
} from 'sentry/views/settings/components/identityIcon';

type TIcon = {
  id: string;
  name: string;
  additionalProps?: string[];
  defaultProps?: Record<string, unknown>;
  groups?: string[];
  keywords?: string[];
};
type TSection = {
  icons: TIcon[];
  id: string;
  label: string;
};

const SECTIONS: TSection[] = [
  {
    id: 'product',
    label: 'Product',
    icons: [
      {
        id: 'dashboard',
        groups: ['product'],
        keywords: ['overview', 'group', 'organize', 'widgets'],
        name: 'Dashboard',
        defaultProps: {},
      },
      {
        id: 'stats',
        groups: ['product'],
        keywords: ['bar', 'graph'],
        name: 'Stats',
        defaultProps: {},
      },
      {
        id: 'project',
        groups: ['product'],
        keywords: [],
        name: 'Project',
        defaultProps: {},
      },
      {
        id: 'issues',
        groups: ['product'],
        keywords: ['stack'],
        name: 'Issues',
        defaultProps: {},
      },
      {
        id: 'releases',
        groups: ['product'],
        keywords: ['stack', 'versions'],
        name: 'Releases',
        defaultProps: {},
      },
      {
        id: 'archive',
        groups: ['product'],
        keywords: [],
        name: 'Archive',
        defaultProps: {},
      },
      {
        id: 'support',
        groups: ['product'],
        keywords: ['microphone', 'help'],
        name: 'Support',
        defaultProps: {},
      },
      {
        id: 'settings',
        groups: ['product'],
        keywords: ['preference'],
        name: 'Settings',
        defaultProps: {},
      },
      {
        id: 'lab',
        groups: ['product'],
        keywords: ['experiment', 'test'],
        name: 'Lab',
        additionalProps: ['isSolid'],
        defaultProps: {
          isSolid: false,
        },
      },
      {
        id: 'lab-isSolid',
        groups: ['product'],
        keywords: ['experiment', 'test'],
        name: 'Lab',
        additionalProps: ['isSolid'],
        defaultProps: {
          isSolid: true,
        },
      },
      {
        id: 'broadcast',
        groups: ['product'],
        keywords: ['stream'],
        name: 'Broadcast',
        defaultProps: {},
      },
      {
        id: 'wifi',
        groups: ['product'],
        keywords: ['internet'],
        name: 'Wifi',
        defaultProps: {},
      },
      {
        id: 'telescope',
        groups: ['product'],
        keywords: [],
        name: 'Telescope',
        defaultProps: {},
      },
      {
        id: 'lightning',
        groups: ['product'],
        keywords: ['feature', 'new', 'fresh'],
        name: 'Lightning',
        defaultProps: {},
      },
      {
        id: 'business',
        groups: ['product'],
        keywords: ['feature', 'promotion', 'fresh', 'new'],
        name: 'Business',
        defaultProps: {},
      },
      {
        id: 'siren',
        groups: ['product'],
        keywords: ['alert', 'important', 'warning'],
        name: 'Siren',
        defaultProps: {},
      },
      {
        id: 'profiling',
        groups: ['product', 'chart'],
        keywords: ['performance', 'span', 'flame', 'icicle'],
        name: 'Profiling',
        defaultProps: {},
      },
      {
        id: 'timer',
        groups: ['product', 'action'],
        keywords: ['cron', 'monitors', 'clock', 'cycle'],
        name: 'Timer',
        defaultProps: {},
      },
      {
        id: 'seer',
        groups: ['product', 'seer'],
        keywords: ['seer', 'ai', 'eye'],
        name: 'Seer',
        defaultProps: {},
      },
      {
        id: 'seer-waiting',
        groups: ['product', 'seer'],
        keywords: ['seer', 'ai', 'eye'],
        name: 'Seer',
        defaultProps: {variant: 'waiting'},
      },
      {
        id: 'seer-loading',
        groups: ['product', 'seer'],
        keywords: ['seer', 'ai', 'eye'],
        name: 'Seer',
        defaultProps: {variant: 'loading'},
      },
      {
        id: 'my-projects',
        groups: ['product'],
        keywords: ['starred', 'sidebar'],
        name: 'MyProjects',
        defaultProps: {},
      },
      {
        id: 'all-projects',
        groups: ['product'],
        keywords: ['starred', 'sidebar'],
        name: 'AllProjects',
        defaultProps: {},
      },
    ],
  },
  {
    id: 'logo',
    label: 'Logos',
    icons: [
      {
        id: 'sentry',
        groups: ['logo'],
        keywords: [],
        name: 'Sentry',
        defaultProps: {},
      },
      {
        id: 'codecov',
        groups: ['logo'],
        keywords: [],
        name: 'Codecov',
        defaultProps: {},
      },
      {
        id: 'bitbucket',
        groups: ['logo'],
        keywords: [],
        name: 'Bitbucket',
        defaultProps: {},
      },
      {
        id: 'discord',
        groups: ['logo'],
        keywords: [],
        name: 'Discord',
        defaultProps: {},
      },
      {
        id: 'github',
        groups: ['logo'],
        keywords: [],
        name: 'Github',
        defaultProps: {},
      },
      {
        id: 'gitlab',
        groups: ['logo'],
        keywords: [],
        name: 'Gitlab',
        defaultProps: {},
      },
      {
        id: 'google',
        groups: ['logo'],
        keywords: [],
        name: 'Google',
        defaultProps: {},
      },
      {
        id: 'jira',
        groups: ['logo'],
        keywords: [],
        name: 'Jira',
        defaultProps: {},
      },
      {
        id: 'trello',
        groups: ['logo'],
        keywords: [],
        name: 'Trello',
        defaultProps: {},
      },
      {
        id: 'vsts',
        groups: ['logo'],
        keywords: [],
        name: 'Vsts',
        defaultProps: {},
      },
      {
        id: 'generic',
        groups: ['logo'],
        keywords: [],
        name: 'Generic',
        defaultProps: {},
      },
      {
        id: 'asana',
        groups: ['logo'],
        keywords: [''],
        name: 'Asana',
        defaultProps: {},
      },
      {
        id: 'vercel',
        groups: ['logo'],
        keywords: [''],
        name: 'Vercel',
        defaultProps: {},
      },
      {
        id: 'teamwork',
        groups: ['logo'],
        keywords: [],
        name: 'Teamwork',
        defaultProps: {},
      },
    ],
  },
  {
    id: 'navigation',
    label: 'Navigation',
    icons: [
      {
        id: 'chevron-direction-left',
        groups: ['navigation'],
        keywords: [
          'up',
          'down',
          'left',
          'right',
          'point',
          'direct',
          'move',
          'expand',
          'collapse',
          'arrow',
          'double',
        ],
        additionalProps: ['isCircled', 'direction', 'isDouble'],
        name: 'Chevron',
        defaultProps: {
          isCircled: false,
          direction: 'left',
          isDouble: false,
        },
      },
      {
        id: 'chevron-direction-right',
        name: 'Chevron',
        defaultProps: {
          isCircled: false,
          direction: 'right',
        },
      },
      {
        id: 'chevron-direction-up',
        name: 'Chevron',
        defaultProps: {
          isCircled: false,
          direction: 'up',
        },
      },
      {
        id: 'chevron-direction-down',
        name: 'Chevron',
        defaultProps: {
          isCircled: false,
          direction: 'down',
        },
      },
      {
        id: 'chevron-isCircled-direction-left',
        name: 'Chevron',
        defaultProps: {
          isCircled: true,
          direction: 'left',
        },
      },
      {
        id: 'chevron-isCircled-direction-right',
        name: 'Chevron',
        defaultProps: {
          isCircled: true,
          direction: 'right',
        },
      },
      {
        id: 'chevron-isCircled-direction-up',
        name: 'Chevron',
        defaultProps: {
          isCircled: true,
          direction: 'up',
        },
      },
      {
        id: 'chevron-isCircled-direction-down',
        name: 'Chevron',
        defaultProps: {
          isCircled: true,
          direction: 'down',
        },
      },
      {
        id: 'chevron-isDouble-direction-left',
        name: 'Chevron',
        defaultProps: {
          isDouble: true,
          direction: 'left',
        },
      },
      {
        id: 'chevron-isDouble-direction-right',
        name: 'Chevron',
        defaultProps: {
          isDouble: true,
          direction: 'right',
        },
      },
      {
        id: 'chevron-isDouble-direction-up',
        name: 'Chevron',
        defaultProps: {
          isDouble: true,
          direction: 'up',
        },
      },
      {
        id: 'chevron-isDouble-direction-down',
        name: 'Chevron',
        defaultProps: {
          isDouble: true,
          direction: 'down',
        },
      },
      {
        id: 'arrow-direction-left',
        groups: ['navigation'],
        keywords: ['up', 'down', 'left', 'right', 'point', 'direct', 'move'],
        additionalProps: ['direction'],
        name: 'Arrow',
        defaultProps: {
          direction: 'left',
        },
      },
      {
        id: 'arrow-direction-right',
        name: 'Arrow',
        defaultProps: {
          direction: 'right',
        },
      },
      {
        id: 'arrow-direction-up',
        name: 'Arrow',
        defaultProps: {
          direction: 'up',
        },
      },
      {
        id: 'arrow-direction-down',
        name: 'Arrow',
        defaultProps: {
          direction: 'down',
        },
      },
      {
        id: 'panel-direction-left',
        groups: ['navigation'],
        keywords: ['sidebar', 'footer', 'header'],
        additionalProps: ['direction'],
        name: 'Panel',
        defaultProps: {
          direction: 'left',
        },
      },
      {
        id: 'panel-direction-right',
        name: 'Panel',
        defaultProps: {
          direction: 'right',
        },
      },
      {
        id: 'panel-direction-up',
        name: 'Panel',
        defaultProps: {
          direction: 'up',
        },
      },
      {
        id: 'panel-direction-down',
        name: 'Panel',
        defaultProps: {
          direction: 'down',
        },
      },
    ],
  },
  {
    id: 'status',
    label: 'Status',
    icons: [
      {
        id: 'lock',
        groups: ['action', 'status'],
        keywords: ['secure'],
        additionalProps: ['locked'],
        name: 'Lock',
        defaultProps: {
          locked: false,
        },
      },
      {
        id: 'lock-locked',
        name: 'Lock',
        defaultProps: {
          locked: true,
        },
      },
      {
        id: 'fire',
        groups: ['status'],
        keywords: ['danger', 'severe', 'critical'],
        name: 'Fire',
        defaultProps: {},
      },
      {
        id: 'fatal',
        groups: ['status'],
        keywords: ['skull'],
        name: 'Fatal',
        defaultProps: {},
      },
      {
        id: 'warning',
        groups: ['status'],
        keywords: ['alert', 'notification'],
        name: 'Warning',
        defaultProps: {},
      },
      {
        id: 'exclamation',
        groups: ['status'],
        keywords: ['alert', 'warning'],
        name: 'Exclamation',
        defaultProps: {},
      },
      {
        id: 'not',
        groups: ['status'],
        keywords: ['invalid', 'no', 'forbidden'],
        name: 'Not',
        defaultProps: {},
      },
      {
        id: 'circle',
        groups: ['status'],
        keywords: ['shape', 'round'],
        name: 'Circle',
        defaultProps: {},
      },
      {
        id: 'circleFill',
        groups: ['status'],
        keywords: ['shape', 'round'],
        name: 'CircleFill',
        defaultProps: {},
      },
      {
        id: 'diamond',
        groups: ['status'],
        keywords: ['shape', 'alert', 'diamond'],
        name: 'Diamond',
        defaultProps: {},
      },
      {
        id: 'flag',
        groups: ['status'],
        keywords: ['bookmark', 'mark', 'save', 'warning', 'message'],
        name: 'Flag',
        defaultProps: {},
      },
      {
        id: 'happy',
        groups: ['status'],
        keywords: ['good'],
        name: 'Happy',
        defaultProps: {},
      },
      {
        id: 'meh',
        groups: ['status'],
        keywords: ['meh'],
        name: 'Meh',
        defaultProps: {},
      },
      {
        id: 'sad',
        groups: ['status'],
        keywords: ['poor'],
        name: 'Sad',
        defaultProps: {},
      },
      {
        id: 'slow',
        groups: ['status'],
        keywords: ['frame', 'mobile'],
        name: 'Slow',
        defaultProps: {},
      },
    ],
  },
  {
    id: 'action',
    label: 'Action',
    icons: [
      {
        id: 'add',
        groups: ['action'],
        keywords: ['plus'],
        additionalProps: ['isCircled'],
        name: 'Add',
        defaultProps: {
          isCircled: false,
        },
      },
      {
        id: 'add-isCircled',
        name: 'Add',
        defaultProps: {
          isCircled: true,
        },
      },
      {
        id: 'subtract',
        groups: ['action'],
        keywords: ['minus'],
        additionalProps: ['isCircled'],
        name: 'Subtract',
        defaultProps: {
          isCircled: false,
        },
      },
      {
        id: 'subtract-isCircled',
        name: 'Subtract',
        defaultProps: {
          isCircled: true,
        },
      },
      {
        id: 'checkmark',
        groups: ['action'],
        keywords: ['done', 'finish', 'success', 'confirm', 'resolve'],
        additionalProps: ['isCircled'],
        name: 'Checkmark',
        defaultProps: {
          isCircled: false,
        },
      },
      {
        id: 'checkmark-isCircled',
        name: 'Checkmark',
        defaultProps: {
          isCircled: true,
        },
      },
      {
        id: 'close',
        groups: ['action'],
        keywords: ['cross', 'deny', 'terminate'],
        additionalProps: ['isCircled'],
        name: 'Close',
        defaultProps: {
          isCircled: false,
        },
      },
      {
        id: 'close-isCircled',
        name: 'Close',
        defaultProps: {
          isCircled: true,
        },
      },
      {
        id: 'divide',
        groups: ['action'],
        keywords: ['divided', 'math'],
        name: 'Divide',
        defaultProps: {},
      },
      {
        id: 'upload',
        groups: ['action'],
        keywords: ['file', 'image', 'up'],
        name: 'Upload',
        defaultProps: {},
      },
      {
        id: 'download',
        groups: ['action'],
        keywords: ['file', 'image', 'down'],
        name: 'Download',
        defaultProps: {},
      },
      {
        id: 'sync',
        groups: ['action'],
        keywords: ['swap'],
        name: 'Sync',
        defaultProps: {},
      },
      {
        id: 'menu',
        groups: ['action'],
        keywords: ['navigate'],
        name: 'Menu',
        defaultProps: {},
      },
      {
        id: 'list',
        groups: ['action'],
        keywords: ['item'],
        name: 'List',
        defaultProps: {},
      },
      {
        id: 'upgrade',
        groups: ['action'],
        keywords: ['up'],
        name: 'Upgrade',
        defaultProps: {},
      },
      {
        id: 'open',
        groups: ['action'],
        keywords: ['link', 'hyperlink', 'external'],
        name: 'Open',
        defaultProps: {},
      },
      {
        id: 'refresh',
        groups: ['action'],
        keywords: ['reload', 'restart', 'repeat'],
        name: 'Refresh',
        defaultProps: {},
      },
      {
        id: 'bookmark',
        groups: ['action'],
        keywords: ['favorite', 'star', 'mark'],
        additionalProps: ['isSolid'],
        name: 'Bookmark',
        defaultProps: {
          isSolid: false,
        },
      },
      {
        id: 'bookmark-isSolid',
        name: 'Bookmark',
        defaultProps: {
          isSolid: true,
        },
      },
      {
        id: 'pin',
        groups: ['action'],
        keywords: ['stick'],
        additionalProps: ['isSolid'],
        name: 'Pin',
        defaultProps: {
          isSolid: false,
        },
      },
      {
        id: 'pin-isSolid',
        name: 'Pin',
        defaultProps: {
          isSolid: true,
        },
      },
      {
        id: 'star',
        groups: ['action'],
        keywords: ['favorite', 'star', 'bookmark'],
        additionalProps: ['isSolid'],
        name: 'Star',
        defaultProps: {
          isSolid: false,
        },
      },
      {
        id: 'star-isSolid',
        name: 'Star',
        defaultProps: {
          isSolid: true,
        },
      },
      {
        id: 'archive',
        groups: ['product'],
        keywords: [],
        name: 'Archive',
        defaultProps: {},
      },
      {
        id: 'play',
        groups: ['action'],
        keywords: ['video', 'audio', 'unpause'],
        name: 'Play',
        defaultProps: {},
      },
      {
        id: 'pause',
        groups: ['action'],
        keywords: ['video', 'audio', 'stop'],
        name: 'Pause',
        defaultProps: {},
      },
      {
        id: 'previous',
        groups: ['action'],
        keywords: ['video', 'audio', 'back', 'rewind'],
        name: 'Previous',
        defaultProps: {},
      },
      {
        id: 'next',
        groups: ['action'],
        keywords: ['video', 'audio', 'skip', 'forward'],
        name: 'Next',
        defaultProps: {},
      },
      {
        id: 'search',
        groups: ['action'],
        keywords: ['find', 'look', 'query'],
        name: 'Search',
        defaultProps: {},
      },
      {
        id: 'copy',
        groups: ['action'],
        keywords: ['duplicate'],
        name: 'Copy',
        defaultProps: {},
      },
      {
        id: 'delete',
        groups: ['action'],
        keywords: ['trash', 'can', 'dumpster', 'remove', 'erase', 'clear'],
        name: 'Delete',
        defaultProps: {},
      },
      {
        id: 'docs',
        groups: ['action'],
        keywords: ['document'],
        name: 'Docs',
        defaultProps: {},
      },
      {
        id: 'link',
        groups: ['action'],
        keywords: ['hyperlink'],
        name: 'Link',
        defaultProps: {},
      },
      {
        id: 'attachment',
        groups: ['action'],
        keywords: ['include', 'clip'],
        name: 'Attachment',
        defaultProps: {},
      },
      {
        id: 'location',
        groups: ['action'],
        keywords: ['pin', 'position', 'map'],
        name: 'Location',
        defaultProps: {},
      },
      {
        id: 'edit',
        groups: ['action'],
        keywords: ['pencil'],
        name: 'Edit',
        defaultProps: {},
      },
      {
        id: 'filter',
        groups: ['action'],
        keywords: [],
        name: 'Filter',
        defaultProps: {},
      },
      {
        id: 'sort',
        groups: ['action'],
        keywords: [],
        name: 'Sort',
        defaultProps: {},
      },
      {
        id: 'show',
        groups: ['action'],
        keywords: ['visible'],
        name: 'Show',
        defaultProps: {},
      },
      {
        id: 'lock',
        name: 'Lock',
        defaultProps: {
          isSolid: false,
        },
      },
      {
        id: 'lock-isSolid',
        name: 'Lock',
        defaultProps: {
          isSolid: true,
        },
      },
      {
        id: 'grabbable',
        groups: ['action'],
        keywords: ['move', 'arrange', 'organize', 'rank', 'switch'],
        name: 'Grabbable',
        defaultProps: {},
      },
      {
        id: 'ellipsis',
        groups: ['action'],
        keywords: ['expand', 'open', 'more', 'hidden'],
        name: 'Ellipsis',
        defaultProps: {},
      },
      {
        id: 'megaphone',
        groups: ['action'],
        keywords: ['speaker', 'announce'],
        name: 'Megaphone',
        defaultProps: {},
      },
      {
        id: 'question',
        groups: ['action'],
        keywords: ['info', 'about', 'information', 'ask', 'faq', 'q&a'],
        name: 'Question',
        defaultProps: {},
      },
      {
        id: 'info',
        groups: ['action'],
        keywords: ['more', 'about', 'information', 'ask', 'faq', 'q&a'],
        name: 'Info',
        defaultProps: {},
      },
      {
        id: 'user',
        groups: ['action'],
        keywords: ['person', 'portrait'],
        name: 'User',
        defaultProps: {},
      },
      {
        id: 'chat',
        groups: ['action', 'action'],
        keywords: ['message', 'bubble'],
        name: 'Chat',
        defaultProps: {},
      },
      {
        id: 'clock',
        groups: ['action'],
        keywords: ['time', 'watch'],
        name: 'Clock',
        defaultProps: {},
      },
      {
        id: 'sliders-direction-left',
        groups: ['action'],
        keywords: ['settings', 'slide', 'adjust'],
        additionalProps: ['direction'],
        name: 'Sliders',
        defaultProps: {
          direction: 'left',
        },
      },
      {
        id: 'sliders-direction-up',
        name: 'Sliders',
        defaultProps: {
          direction: 'up',
        },
      },
      {
        id: 'fix',
        groups: ['action'],
        keywords: ['wrench', 'resolve'],
        name: 'Fix',
        defaultProps: {},
      },
      {
        id: 'tag',
        groups: ['action'],
        keywords: ['price', 'category', 'group'],
        name: 'Tag',
        defaultProps: {},
      },
      {
        id: 'moon',
        groups: ['action'],
        keywords: ['dark', 'night'],
        name: 'Moon',
        defaultProps: {},
      },
      {
        id: 'subscribed',
        groups: ['action'],
        keywords: ['alert', 'notification', 'subscribe', 'bell', 'ring'],
        name: 'Subscribed',
        defaultProps: {},
      },
      {
        id: 'unsubscribed',
        groups: ['action'],
        keywords: ['alert', 'notification', 'subscribe', 'bell', 'ring'],
        name: 'Unsubscribed',
        defaultProps: {},
      },
      {
        id: 'sound',
        groups: ['action'],
        keywords: ['audio'],
        name: 'Sound',
        defaultProps: {},
      },
      {
        id: 'mute',
        groups: ['action'],
        keywords: ['audio'],
        name: 'Mute',
        defaultProps: {},
      },
      {
        id: 'resize',
        groups: ['action'],
        keywords: ['scale', 'stretch'],
        name: 'Resize',
        defaultProps: {},
      },
      {
        id: 'expand',
        groups: ['action'],
        keywords: ['open'],
        name: 'Expand',
        defaultProps: {},
      },
      {
        id: 'contract',
        groups: ['action'],
        keywords: ['close'],
        name: 'Contract',
        defaultProps: {},
      },
      {
        id: 'group',
        groups: ['action'],
        keywords: ['users', 'person', 'people'],
        name: 'Group',
        defaultProps: {},
      },
      {
        id: 'rewind10',
        groups: ['action'],
        keywords: ['rewind'],
        name: 'Rewind10',
        defaultProps: {},
      },
      {
        id: 'timer',
        name: 'Timer',
        defaultProps: {},
      },
      {
        id: 'cursorArrow',
        keywords: ['pointer', 'mouse'],
        name: 'CursorArrow',
        defaultProps: {},
      },
      {
        id: 'keyDown',
        keywords: ['keyboard', 'press', 'click', 'tap'],
        name: 'KeyDown',
        defaultProps: {},
      },
      {
        id: 'zoom-out',
        keywords: [],
        name: 'Zoom',
        defaultProps: {isZoomIn: false},
      },
      {
        id: 'zoom-in',
        keywords: [],
        name: 'Zoom',
        defaultProps: {isZoomIn: true},
      },
      {
        id: 'focus',
        keywords: ['foreground'],
        name: 'Focus',
        defaultProps: {isFocused: true},
      },
      {
        id: 'blur',
        keywords: ['background'],
        name: 'Focus',
        defaultProps: {isFocused: false},
      },
      {
        id: 'tap',
        keywords: ['finger', 'hand', 'cursor'],
        name: 'Tap',
        defaultProps: {},
      },
      {
        id: 'thumb',
        keywords: ['feedback', 'good'],
        additionalProps: ['direction'],
        name: 'Thumb',
        defaultProps: {},
      },
      {
        id: 'thumb',
        keywords: ['feedback', 'bad', 'poor'],
        additionalProps: ['direction'],
        name: 'Thumb',
        defaultProps: {
          direction: ['down'],
        },
      },
    ],
  },
  {
    id: 'chart',
    label: 'Visualizations',
    icons: [
      {
        id: 'graph-type-line',
        groups: ['chart'],
        keywords: ['line', 'plot'],
        additionalProps: ['type'],
        name: 'Graph',
        defaultProps: {
          type: 'line',
        },
      },
      {
        id: 'graph-type-circle',
        name: 'Graph',
        defaultProps: {
          type: 'circle',
        },
      },
      {
        id: 'graph-type-bar',
        name: 'Graph',
        defaultProps: {
          type: 'bar',
        },
      },
      {
        id: 'graph-type-area',
        name: 'Graph',
        defaultProps: {
          type: 'area',
        },
      },
      {
        id: 'graph-type-scatter',
        name: 'Graph',
        defaultProps: {
          type: 'scatter',
        },
      },
      {
        id: 'stack',
        groups: ['chart'],
        keywords: ['group', 'combine', 'view'],
        name: 'Stack',
        defaultProps: {},
      },
      {
        id: 'span',
        groups: ['chart'],
        keywords: ['performance', 'transaction'],
        name: 'Span',
        defaultProps: {},
      },
      {
        id: 'number',
        groups: ['chart'],
        keywords: ['value'],
        name: 'Number',
        defaultProps: {},
      },
      {
        id: 'profiling',
        name: 'Profiling',
        defaultProps: {},
      },
      {
        id: 'table',
        name: 'Table',
        defaultProps: {},
      },
      {
        id: 'grid',
        name: 'Grid',
        keywords: ['squares', 'layout'],
        defaultProps: {},
      },
      {
        id: 'globe',
        name: 'Globe',
        keywords: ['map', 'international'],
        defaultProps: {},
      },
    ],
  },
  {
    id: 'device',
    label: 'Device',
    icons: [
      {
        id: 'file',
        groups: ['device'],
        keywords: ['document'],
        name: 'File',
        defaultProps: {},
      },
      {
        id: 'print',
        groups: ['device'],
        keywords: [],
        name: 'Print',
        defaultProps: {},
      },
      {
        id: 'code',
        groups: ['device'],
        keywords: ['snippet', 'javascript', 'json', 'curly', 'source'],
        name: 'Code',
        defaultProps: {},
      },
      {
        id: 'json',
        groups: ['device'],
        keywords: ['snippet', 'code', 'javascript', 'source'],
        name: 'Json',
        defaultProps: {},
      },
      {
        id: 'markdown',
        groups: ['device'],
        keywords: ['code'],
        name: 'Markdown',
        defaultProps: {},
      },
      {
        id: 'terminal',
        groups: ['device', 'device'],
        keywords: ['code', 'bash', 'command'],
        name: 'Terminal',
        defaultProps: {},
      },
      {
        id: 'commit',
        groups: ['device'],
        keywords: ['git', 'github'],
        name: 'Commit',
        defaultProps: {},
      },
      {
        id: 'laptop',
        groups: ['device'],
        keywords: ['computer', 'macbook'],
        name: 'Laptop',
        defaultProps: {},
      },
      {
        id: 'mobile',
        groups: ['device'],
        keywords: ['phone', 'iphone'],
        name: 'Mobile',
        defaultProps: {},
      },
      {
        id: 'window',
        groups: ['device'],
        keywords: ['application'],
        name: 'Window',
        defaultProps: {},
      },
      {
        id: 'calendar',
        groups: ['device'],
        keywords: ['time', 'date'],
        name: 'Calendar',
        defaultProps: {},
      },
      {
        id: 'mail',
        groups: ['device'],
        keywords: ['email'],
        name: 'Mail',
        defaultProps: {},
      },
      {
        id: 'input',
        groups: ['device'],
        keywords: ['text'],
        name: 'Input',
        defaultProps: {},
      },
      {
        id: 'fileBroken',
        groups: ['device'],
        keywords: ['file', 'missing', 'error'],
        name: 'FileBroken',
        defaultProps: {},
      },
      {
        id: 'image',
        groups: ['device'],
        keywords: ['image', 'photo', 'screenshot'],
        name: 'Image',
        defaultProps: {},
      },
    ],
  },
];

export default function IconsStories() {
  const [searchTerm, setSearchTerm] = useState('');

  const definedWithPrefix = new Set<string>();

  SECTIONS.forEach(section =>
    section.icons.forEach(icon => definedWithPrefix.add(`Icon${icon.name}`))
  );

  const unclassifiedSection = {
    id: 'other',
    label: 'Unclassified',
    icons: Object.keys(Icons)
      .filter(name => !definedWithPrefix.has(name))
      .map((name): TIcon => ({id: name, name})),
  };

  const filteredSections = searchTerm
    ? SECTIONS.map(section => ({
        ...section,
        icons: section.icons.filter(
          icon =>
            icon.name.toLowerCase().includes(searchTerm) ||
            icon.keywords?.some(keyword => keyword.toLowerCase().includes(searchTerm))
        ),
      }))
    : SECTIONS;

  return (
    <Fragment>
      <StyledSticky>
        <p>
          In addition to icon name, you can also search by keyword. For example, typing
          either <kbd>checkmark</kbd> or <kbd>success</kbd> will return{' '}
          <samp>IconCheckmark</samp>.
        </p>
        <Input
          placeholder="Search icons by name or keyword"
          onChange={e => setSearchTerm(e.target.value.toLowerCase())}
        />
      </StyledSticky>

      <Section section={unclassifiedSection} />

      {filteredSections.map(section => (
        <Section key={section.id} section={section} />
      ))}

      <PluginIconsSection searchTerm={searchTerm} />
      <IdentityIconsSection searchTerm={searchTerm} />
      <PlatformIconsSection searchTerm={searchTerm} />
    </Fragment>
  );
}

function Section({section}: {section: TSection}) {
  if (section.icons.length === 0) {
    return null;
  }

  return (
    <section>
      <SectionHeader>{section.label}</SectionHeader>
      <p>
        <code>{"import { ... } from 'sentry/icons';"}</code>
      </p>
      <Grid style={{gridTemplateColumns: 'repeat(4, 1fr)'}}>
        {section.icons.map(icon => {
          const name = icon.name.startsWith('Icon') ? icon.name : `Icon${icon.name}`;
          // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
          const Component = Icons[name];

          if (!Component) {
            // The definition is not type safe, so lets log the icon instead of throwing an error
            // eslint-disable-next-line no-console
            console.log('Missing icon', name);
            return null;
          }

          const props = {color: 'gray500', size: 'sm', ...icon.defaultProps};
          return (
            <Tooltip
              key={icon.id}
              isHoverable
              overlayStyle={{maxWidth: 440}}
              title={<Storybook.JSXNode name={name} props={props} />}
            >
              <Cell>
                <Component {...props} />
                {name}
              </Cell>
            </Tooltip>
          );
        })}
      </Grid>
    </section>
  );
}

function PlatformIconsSection({searchTerm}: {searchTerm: string}) {
  const filteredPlatforms = platforms.filter(platform => platform.includes(searchTerm));

  return (
    <section>
      <SectionHeader>PlatformIcons</SectionHeader>
      <p>
        <code>{"import {PlatformIcon} from 'platformicons';"}</code>
      </p>
      <Grid
        style={{
          gridAutoFlow: 'column',
          gridTemplateRows: `repeat(${Math.ceil(filteredPlatforms.length / 4)}, 1fr)`,
        }}
      >
        {filteredPlatforms.map(platform => (
          <Tooltip
            key={platform}
            isHoverable
            overlayStyle={{maxWidth: 440}}
            title={
              <Fragment>
                <Storybook.JSXNode name="PlatformIcon" props={{platform}} />
              </Fragment>
            }
          >
            <Cell>
              <PlatformIcon platform={platform} /> {platform}
            </Cell>
          </Tooltip>
        ))}
      </Grid>
    </section>
  );
}

const PLUGIN_ICON_KEYS: Array<PluginIconProps['pluginId']> = [
  'placeholder',
  'sentry',
  'browsers',
  'device',
  'interface_types',
  'os',
  'urls',
  'webhooks',
  'amazon-sqs',
  'aws_lambda',
  'asana',
  'bitbucket',
  'bitbucket_pipelines',
  'bitbucket_server',
  'discord',
  'github',
  'github_enterprise',
  'gitlab',
  'heroku',
  'jira',
  'jira_server',
  'jumpcloud',
  'msteams',
  'opsgenie',
  'pagerduty',
  'pivotal',
  'pushover',
  'redmine',
  'segment',
  'slack',
  'trello',
  'twilio',
  'visualstudio',
  'vsts',
  'vercel',
  'victorops',
];

const PLUGIN_ICONS = PLUGIN_ICON_KEYS.map(key => ({
  id: key,
  name: key,
  keywords: [key],
  icons: [{id: key, name: key}],
}));

function PluginIconsSection({searchTerm}: {searchTerm: string}) {
  const filteredPlatforms = PLUGIN_ICONS.filter(icon => icon.name.includes(searchTerm));

  return (
    <section>
      <SectionHeader>PluginIcons</SectionHeader>
      <p>
        <code>{"import {PluginIcon} from 'sentry/plugins/components/pluginIcon';"}</code>
      </p>
      <Grid
        style={{
          gridAutoFlow: 'column',
          gridTemplateRows: `repeat(${Math.ceil(filteredPlatforms.length / 4)}, 1fr)`,
        }}
      >
        {filteredPlatforms.map(platform => (
          <Tooltip
            key={platform.id}
            isHoverable
            overlayStyle={{maxWidth: 440}}
            title={
              <Fragment>
                <Storybook.JSXNode name="PluginIcon" props={{pluginId: platform.id}} />
              </Fragment>
            }
          >
            <Cell>
              <PluginIcon pluginId={platform.id} /> {platform.name}
            </Cell>
          </Tooltip>
        ))}
      </Grid>
    </section>
  );
}

const IDENTITY_ICON_KEYS: Array<IdentityIconProps['providerId']> = [
  'placeholder',
  'active-directory',
  'asana',
  'auth0',
  'bitbucket',
  'bitbucket_server',
  'github',
  'github_enterprise',
  'gitlab',
  'google',
  'jira_server',
  'jumpcloud',
  'msteams',
  'okta',
  'onelogin',
  'rippling',
  'saml2',
  'slack',
  'visualstudio',
  'vsts',
];

const IDENTITY_ICONS = IDENTITY_ICON_KEYS.map(key => ({
  id: key,
  name: key,
  keywords: [key],
  icons: [{id: key, name: key}],
}));

function IdentityIconsSection({searchTerm}: {searchTerm: string}) {
  const filteredPlatforms = IDENTITY_ICONS.filter(icon => icon.name.includes(searchTerm));

  return (
    <section>
      <SectionHeader>IdentityIcons</SectionHeader>
      <p>
        <code>
          {"import {IdentityIcon} from 'sentry/views/settings/components/identityIcon';"}
        </code>
      </p>
      <Grid
        style={{
          gridAutoFlow: 'column',
          gridTemplateRows: `repeat(${Math.ceil(filteredPlatforms.length / 4)}, 1fr)`,
        }}
      >
        {filteredPlatforms.map(platform => (
          <Tooltip
            key={platform.id}
            isHoverable
            overlayStyle={{maxWidth: 440}}
            title={
              <Fragment>
                <Storybook.JSXNode
                  name="IdentityIcon"
                  props={{providerId: platform.id}}
                />
              </Fragment>
            }
          >
            <Cell>
              <IdentityIcon providerId={platform.id} /> {platform.name}
            </Cell>
          </Tooltip>
        ))}
      </Grid>
    </section>
  );
}

const StyledSticky = styled(Sticky)`
  background: ${p => p.theme.background};
  z-index: ${p => p.theme.zIndex.initial};
  &[data-stuck='true'] {
    box-shadow: 0px 10px 20px -8px rgba(128, 128, 128, 0.89);
  }
`;

// Large scroll margin top due to sticky header
const SectionHeader = styled('h5')`
  margin-block: ${space(2)};
  scroll-margin-top: 96px;
`;

const Grid = styled('div')`
  display: grid;
  gap: ${space(1)};
  align-items: center;
`;

const Cell = styled('div')`
  display: flex;
  gap: ${space(1)};
  align-items: center;
  border: 1px solid transparent;
  border-radius: ${p => p.theme.borderRadius};
  padding: ${space(1)};
  cursor: pointer;

  &:hover {
    border-color: ${p => p.theme.border};
  }
`;
