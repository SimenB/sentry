import {Fragment} from 'react';
import {useTheme} from '@emotion/react';
import styled from '@emotion/styled';

import InteractionStateLayer from 'sentry/components/core/interactionStateLayer';
import {ExternalLink} from 'sentry/components/core/link';
import {Tooltip} from 'sentry/components/core/tooltip';
import QuestionTooltip from 'sentry/components/questionTooltip';
import {t, tct} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import getDuration from 'sentry/utils/duration/getDuration';
import {VITAL_DESCRIPTIONS} from 'sentry/views/insights/browser/webVitals/components/webVitalDescription';
import {MODULE_DOC_LINK} from 'sentry/views/insights/browser/webVitals/settings';
import type {
  ProjectScore,
  WebVitals,
} from 'sentry/views/insights/browser/webVitals/types';
import {makePerformanceScoreColors} from 'sentry/views/insights/browser/webVitals/utils/performanceScoreColors';
import {
  scoreToStatus,
  STATUS_TEXT,
} from 'sentry/views/insights/browser/webVitals/utils/scoreToStatus';

export type ProjectData = {
  'p75(measurements.cls)': number;
  'p75(measurements.fcp)': number;
  'p75(measurements.inp)': number;
  'p75(measurements.lcp)': number;
  'p75(measurements.ttfb)': number;
};

type Props = {
  onClick?: (webVital: WebVitals) => void;
  projectData?: ProjectData[];
  projectScore?: ProjectScore;
  showTooltip?: boolean;
  transaction?: string;
};

export const WEB_VITALS_METERS_CONFIG = {
  lcp: {
    name: t('Largest Contentful Paint'),
    formatter: (value: number) => getFormattedDuration(value / 1000),
  },
  fcp: {
    name: t('First Contentful Paint'),
    formatter: (value: number) => getFormattedDuration(value / 1000),
  },
  inp: {
    name: t('Interaction to Next Paint'),
    formatter: (value: number) => getFormattedDuration(value / 1000),
  },
  cls: {
    name: t('Cumulative Layout Shift'),
    formatter: (value: number) => Math.round(value * 100) / 100,
  },
  ttfb: {
    name: t('Time To First Byte'),
    formatter: (value: number) => getFormattedDuration(value / 1000),
  },
};

export default function WebVitalMeters({
  onClick,
  projectData,
  projectScore,
  showTooltip = true,
}: Props) {
  const theme = useTheme();
  if (!projectScore) {
    return null;
  }

  const webVitalsConfig = WEB_VITALS_METERS_CONFIG;

  const webVitals = Object.keys(webVitalsConfig) as WebVitals[];
  const colors = theme.chart.getColorPalette(4);

  const renderVitals = () => {
    return webVitals.map((webVital, index) => {
      const webVitalKey: keyof ProjectData = `p75(measurements.${webVital})`;
      const score = projectScore[`${webVital}Score`];
      const meterValue = projectData?.[0]?.[webVitalKey];

      if (!score) {
        return null;
      }

      return (
        <VitalMeter
          key={webVital}
          webVital={webVital}
          showTooltip={showTooltip}
          score={score}
          meterValue={meterValue}
          color={colors[index]!}
          onClick={onClick}
        />
      );
    });
  };

  return (
    <Container>
      <Flex>{renderVitals()}</Flex>
    </Container>
  );
}

type VitalMeterProps = {
  color: string;
  meterValue: number | undefined;
  score: number | undefined;
  showTooltip: boolean;
  webVital: WebVitals;
  isAggregateMode?: boolean;
  onClick?: (webVital: WebVitals) => void;
};

function VitalMeter({
  webVital,
  showTooltip,
  score,
  meterValue,
  color,
  onClick,
  isAggregateMode = true,
}: VitalMeterProps) {
  const webVitalsConfig = WEB_VITALS_METERS_CONFIG;
  const webVitalExists = score !== undefined;

  const formattedMeterValueText =
    webVitalExists && meterValue ? (
      webVitalsConfig[webVital].formatter(meterValue)
    ) : (
      <NoValue />
    );

  const webVitalKey = `measurements.${webVital}`;
  // @ts-expect-error TS(7053): Element implicitly has an 'any' type because expre... Remove this comment to see the full error message
  const {shortDescription} = VITAL_DESCRIPTIONS[webVitalKey];

  const headerText = webVitalsConfig[webVital].name;
  const meterBody = (
    <Fragment>
      <MeterBarBody>
        {showTooltip && (
          <StyledQuestionTooltip
            isHoverable
            size="xs"
            title={
              <span>
                {shortDescription}
                <br />
                <ExternalLink href={`${MODULE_DOC_LINK}#performance-score`}>
                  {t('Find out how performance scores are calculated here.')}
                </ExternalLink>
              </span>
            }
          />
        )}
        <MeterHeader>{headerText}</MeterHeader>
        <MeterValueText>
          <Dot color={color} />
          {formattedMeterValueText}
        </MeterValueText>
      </MeterBarBody>
      <MeterBarFooter score={score} />
    </Fragment>
  );
  return (
    <VitalContainer
      key={webVital}
      webVital={webVital}
      webVitalExists={webVitalExists}
      meterBody={meterBody}
      onClick={onClick}
      isAggregateMode={isAggregateMode}
    />
  );
}

type VitalContainerProps = {
  meterBody: React.ReactNode;
  webVital: WebVitals;
  webVitalExists: boolean;
  isAggregateMode?: boolean;
  onClick?: (webVital: WebVitals) => void;
};

function VitalContainer({
  webVital,
  webVitalExists,
  meterBody,
  onClick,
  isAggregateMode = true,
}: VitalContainerProps) {
  return (
    <MeterBarContainer
      key={webVital}
      onClick={() => webVitalExists && onClick?.(webVital)}
      clickable={webVitalExists}
    >
      {webVitalExists && <InteractionStateLayer />}
      {webVitalExists && meterBody}
      {!webVitalExists && (
        <StyledTooltip
          title={tct('No [webVital] data found in this [selection].', {
            webVital: webVital.toUpperCase(),
            selection: isAggregateMode ? 'project' : 'trace',
          })}
        >
          {meterBody}
        </StyledTooltip>
      )}
    </MeterBarContainer>
  );
}

export const getFormattedDuration = (value: number) => {
  return getDuration(value, value < 1 ? 0 : 2, true);
};

const Container = styled('div')`
  margin-bottom: ${space(1)};
`;

const Flex = styled('div')<{gap?: number}>`
  display: flex;
  flex-direction: row;
  justify-content: center;
  width: 100%;
  gap: ${p => (p.gap ? `${p.gap}px` : space(1))};
  align-items: center;
  flex-wrap: wrap;
`;

const MeterBarContainer = styled('div')<{clickable?: boolean}>`
  background-color: ${p => p.theme.background};
  flex: 1;
  position: relative;
  padding: 0;
  cursor: ${p => (p.clickable ? 'pointer' : 'default')};
  min-width: 140px;
`;

const MeterBarBody = styled('div')`
  border: 1px solid ${p => p.theme.border};
  border-radius: ${p => p.theme.borderRadius} ${p => p.theme.borderRadius} 0 0;
  border-bottom: none;
  padding: ${space(1)} 0 ${space(0.5)} 0;
`;

const MeterHeader = styled('div')`
  font-size: ${p => p.theme.fontSize.sm};
  font-weight: ${p => p.theme.fontWeight.bold};
  color: ${p => p.theme.textColor};
  display: inline-block;
  text-align: center;
  width: 100%;
`;

const MeterValueText = styled('div')`
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: ${p => p.theme.headerFontSize};
  color: ${p => p.theme.textColor};
  flex: 1;
  text-align: center;
`;

function MeterBarFooter({score}: {score: number | undefined}) {
  if (score === undefined) {
    return (
      <MeterBarFooterContainer status="none">{t('No Data')}</MeterBarFooterContainer>
    );
  }
  const status = scoreToStatus(score);
  return (
    <MeterBarFooterContainer status={status}>
      {STATUS_TEXT[status]} {score}
    </MeterBarFooterContainer>
  );
}

const MeterBarFooterContainer = styled('div')<{
  status: keyof ReturnType<typeof makePerformanceScoreColors>;
}>`
  color: ${p => makePerformanceScoreColors(p.theme)[p.status].normal};
  border-radius: 0 0 ${p => p.theme.borderRadius} ${p => p.theme.borderRadius};
  background-color: ${p => makePerformanceScoreColors(p.theme)[p.status].light};
  border: solid 1px ${p => makePerformanceScoreColors(p.theme)[p.status].border};
  font-size: ${p => p.theme.fontSize.xs};
  padding: ${space(0.5)};
  text-align: center;
`;

const NoValueContainer = styled('span')`
  color: ${p => p.theme.subText};
  font-size: ${p => p.theme.headerFontSize};
`;

function NoValue() {
  return <NoValueContainer>{' \u2014 '}</NoValueContainer>;
}

const StyledTooltip = styled(Tooltip)`
  display: block;
  width: 100%;
`;

const StyledQuestionTooltip = styled(QuestionTooltip)`
  position: absolute;
  right: ${space(1)};
`;

export const Dot = styled('span')<{color: string}>`
  display: inline-block;
  margin-right: ${space(1)};
  border-radius: ${p => p.theme.borderRadius};
  width: ${space(1)};
  height: ${space(1)};
  background-color: ${p => p.color};
`;
