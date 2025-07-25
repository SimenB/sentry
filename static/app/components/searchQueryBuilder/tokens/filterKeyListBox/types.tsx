import type {ReactNode} from 'react';

import type {
  SelectOptionWithKey,
  SelectSectionWithKey,
} from 'sentry/components/core/compactSelect/types';

export interface KeyItem extends SelectOptionWithKey<string> {
  description: string;
  details: React.ReactNode;
  hideCheck: boolean;
  showDetailsInOverlay: boolean;
  textValue: string;
  type: 'item';
  value: string;
}

export interface KeySectionItem extends SelectSectionWithKey<string> {
  options: SearchKeyItem[];
  type: 'section';
  value: string;
}

export interface RawSearchItem extends SelectOptionWithKey<string> {
  type: 'raw-search';
  value: string;
}

export interface FilterValueItem extends SelectOptionWithKey<string> {
  type: 'filter-value';
  value: string;
}

export interface RawSearchFilterIsValueItem extends SelectOptionWithKey<string> {
  type: 'raw-search-filter-is-value';
  value: string;
}

export interface RawSearchFilterHasValueItem extends SelectOptionWithKey<string> {
  type: 'raw-search-filter-has-value';
  value: string;
}

interface RecentFilterItem extends SelectOptionWithKey<string> {
  type: 'recent-filter';
  value: string;
}

export interface RecentQueryItem extends SelectOptionWithKey<string> {
  hideCheck: boolean;
  type: 'recent-query';
  value: string;
}

export interface AskSeerItem extends SelectOptionWithKey<string> {
  hideCheck: boolean;
  type: 'ask-seer';
  value: string;
}

export interface AskSeerConsentItem extends SelectOptionWithKey<string> {
  type: 'ask-seer-consent';
  value: string;
}

export type SearchKeyItem =
  | KeySectionItem
  | KeyItem
  | RawSearchItem
  | FilterValueItem
  | RawSearchFilterIsValueItem
  | RawSearchFilterHasValueItem
  | AskSeerItem
  | AskSeerConsentItem;

export type FilterKeyItem =
  | KeyItem
  | RecentFilterItem
  | KeySectionItem
  | RecentQueryItem
  | RawSearchItem
  | FilterValueItem
  | RawSearchFilterIsValueItem
  | RawSearchFilterHasValueItem
  | AskSeerItem
  | AskSeerConsentItem;

export type Section = {
  label: ReactNode;
  value: string;
};
