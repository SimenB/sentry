import {Fragment} from 'react';
import type {Location} from 'history';

import type {CursorHandler} from 'sentry/components/pagination';
import type {GridColumnOrder} from 'sentry/components/tables/gridEditable';
import type {Organization} from 'sentry/types/organization';
import type {Project} from 'sentry/types/project';
import type EventView from 'sentry/utils/discover/eventView';
import SegmentExplorerQuery from 'sentry/utils/performance/segmentExplorer/segmentExplorerQuery';
import TagKeyHistogramQuery from 'sentry/utils/performance/segmentExplorer/tagKeyHistogramQuery';
import {decodeScalar, decodeSorts} from 'sentry/utils/queryString';
import {useNavigate} from 'sentry/utils/useNavigate';

import TagsHeatMap from './tagsHeatMap';
import {TagValueTable} from './tagValueTable';
import {getTagSortForTagsPage} from './utils';

type Props = {
  aggregateColumn: string;
  eventView: EventView;
  location: Location;
  organization: Organization;
  projects: Project[];
  transactionName: string;
  tagKey?: string;
};

const HISTOGRAM_TAG_KEY_LIMIT = 8;
const HISTOGRAM_BUCKET_LIMIT = 40;
export const TAG_PAGE_TABLE_CURSOR = 'tableCursor';

export type TagsTableColumnKeys =
  | 'key'
  | 'tagValue'
  | 'aggregate'
  | 'frequency'
  | 'comparison'
  | 'sumdelta'
  | 'action'
  | 'count';

export type TagsTableColumn = GridColumnOrder<TagsTableColumnKeys> & {
  column: {
    kind: string;
  };
  field: string;
  canSort?: boolean;
};
export const TAGS_TABLE_COLUMN_ORDER: TagsTableColumn[] = [
  {
    key: 'tagValue',
    field: 'tagValue',
    name: 'Tag Values',
    width: -1,
    column: {
      kind: 'field',
    },
  },
  {
    key: 'frequency',
    field: 'frequency',
    name: 'Frequency',
    width: -1,
    column: {
      kind: 'field',
    },
    canSort: true,
  },
  {
    key: 'count',
    field: 'count',
    name: 'Events',
    width: -1,
    column: {
      kind: 'field',
    },
    canSort: true,
  },
  {
    key: 'aggregate',
    field: 'aggregate',
    name: 'Avg Duration',
    width: -1,
    column: {
      kind: 'field',
    },
    canSort: true,
  },
  {
    key: 'action',
    field: 'action',
    name: '',
    width: -1,
    column: {
      kind: 'field',
    },
  },
];

function TagsDisplay(props: Props) {
  const navigate = useNavigate();
  const {eventView: _eventView, location, organization, aggregateColumn, tagKey} = props;
  const eventView = _eventView.clone();

  const handleCursor: CursorHandler = (cursor, pathname, query) =>
    navigate({
      pathname,
      query: {...query, [TAG_PAGE_TABLE_CURSOR]: cursor},
    });

  const cursor = decodeScalar(location.query?.[TAG_PAGE_TABLE_CURSOR]);

  const tagSort = getTagSortForTagsPage(location);

  const tagSorts = decodeSorts(tagSort);

  eventView.fields = TAGS_TABLE_COLUMN_ORDER;

  const sortedEventView = eventView.withSorts(
    tagSorts.length
      ? tagSorts
      : [
          {
            field: 'frequency',
            kind: 'desc',
          },
        ]
  );

  return (
    <Fragment>
      {tagKey ? (
        <Fragment>
          <TagKeyHistogramQuery
            eventView={eventView}
            orgSlug={organization.slug}
            location={location}
            aggregateColumn={aggregateColumn}
            numBucketsPerKey={HISTOGRAM_BUCKET_LIMIT}
            tagKey={tagKey}
            limit={HISTOGRAM_TAG_KEY_LIMIT}
            cursor={cursor}
            sort={tagSort ?? '-sumdelta'}
          >
            {({isLoading, tableData}) => {
              return (
                <TagsHeatMap
                  {...props}
                  tagKey={tagKey}
                  aggregateColumn={aggregateColumn}
                  tableData={tableData}
                  isLoading={isLoading}
                />
              );
            }}
          </TagKeyHistogramQuery>
          <SegmentExplorerQuery
            eventView={sortedEventView}
            orgSlug={organization.slug}
            location={location}
            aggregateColumn={aggregateColumn}
            tagKey={tagKey}
            limit={HISTOGRAM_TAG_KEY_LIMIT}
            cursor={cursor}
            sort={tagSort}
            allTagKeys
          >
            {({isLoading, tableData, pageLinks}) => {
              return (
                <TagValueTable
                  {...props}
                  eventView={sortedEventView}
                  tagKey={tagKey}
                  aggregateColumn={aggregateColumn}
                  pageLinks={pageLinks}
                  tableData={tableData}
                  isLoading={isLoading}
                  onCursor={handleCursor}
                />
              );
            }}
          </SegmentExplorerQuery>
        </Fragment>
      ) : (
        <Fragment>
          <TagsHeatMap
            {...props}
            aggregateColumn={aggregateColumn}
            tableData={null}
            isLoading={false}
          />
          <TagValueTable
            {...props}
            pageLinks={null}
            aggregateColumn={aggregateColumn}
            tableData={null}
            isLoading={false}
          />
        </Fragment>
      )}
    </Fragment>
  );
}

export default TagsDisplay;
