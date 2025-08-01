import {Fragment, useEffect, useMemo, useRef, useState} from 'react';
import {createPortal} from 'react-dom';
import styled from '@emotion/styled';
import {type Change, diffWords} from 'diff';

import {addErrorMessage} from 'sentry/actionCreators/indicator';
import {Button} from 'sentry/components/core/button';
import InteractionStateLayer from 'sentry/components/core/interactionStateLayer';
import {TextArea} from 'sentry/components/core/textarea';
import {AutofixHighlightWrapper} from 'sentry/components/events/autofix/autofixHighlightWrapper';
import {
  type DiffLine,
  DiffLineType,
  type FilePatch,
} from 'sentry/components/events/autofix/types';
import {makeAutofixQueryKey} from 'sentry/components/events/autofix/useAutofix';
import {DIFF_COLORS} from 'sentry/components/splitDiff';
import {IconChevron, IconClose, IconDelete, IconEdit} from 'sentry/icons';
import {t} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import {useMutation, useQueryClient} from 'sentry/utils/queryClient';
import useApi from 'sentry/utils/useApi';
import useOrganization from 'sentry/utils/useOrganization';
import {usePrismTokens} from 'sentry/utils/usePrismTokens';

type AutofixDiffProps = {
  diff: FilePatch[];
  editable: boolean;
  groupId: string;
  runId: string;
  integratedStyle?: boolean;
  previousDefaultStepIndex?: number;
  previousInsightCount?: number;
  repoId?: string;
};

interface DiffLineWithChanges extends DiffLine {
  changes?: Change[];
}

function makeTestIdFromLineType(lineType: DiffLineType) {
  switch (lineType) {
    case DiffLineType.ADDED:
      return 'line-added';
    case DiffLineType.REMOVED:
      return 'line-removed';
    default:
      return 'line-context';
  }
}

function addChangesToDiffLines(lines: DiffLineWithChanges[]): DiffLineWithChanges[] {
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]!;
    if (line.line_type === DiffLineType.CONTEXT) {
      continue;
    }

    if (line.line_type === DiffLineType.REMOVED) {
      const prevLine = lines[i - 1];
      const nextLine = lines[i + 1];
      const nextNextLine = lines[i + 2];

      if (
        nextLine?.line_type === DiffLineType.ADDED &&
        prevLine?.line_type !== DiffLineType.REMOVED &&
        nextNextLine?.line_type !== DiffLineType.ADDED
      ) {
        const changes = diffWords(line.value, nextLine.value);
        lines[i] = {...line, changes: changes.filter(change => !change.added)};
        lines[i + 1] = {...nextLine, changes: changes.filter(change => !change.removed)};
      }
    }
  }

  return lines;
}

function detectLanguageFromPath(filePath: string): string {
  if (!filePath) {
    return 'plaintext';
  }
  const extension = filePath.split('.').pop()?.toLowerCase();
  if (!extension) {
    return 'plaintext';
  }

  // Map common file extensions to Prism language identifiers
  const extensionMap: Record<string, string> = {
    js: 'javascript',
    jsx: 'jsx',
    ts: 'typescript',
    tsx: 'tsx',
    py: 'python',
    rb: 'ruby',
    go: 'go',
    java: 'java',
    php: 'php',
    c: 'c',
    cpp: 'cpp',
    cs: 'csharp',
    html: 'html',
    css: 'css',
    scss: 'scss',
    json: 'json',
    md: 'markdown',
    yaml: 'yaml',
    yml: 'yaml',
    sh: 'bash',
    bash: 'bash',
    rs: 'rust',
    swift: 'swift',
    kt: 'kotlin',
    sql: 'sql',
    xml: 'xml',
  };

  return extensionMap[extension] || 'plaintext';
}

const SyntaxHighlightedCode = styled('div')`
  font-family: ${p => p.theme.text.familyMono};
  white-space: pre;

  && pre,
  && code {
    margin: 0;
    padding: 0;
    background: transparent;
  }
`;

function DiffLineCode({line, fileName}: {line: DiffLineWithChanges; fileName?: string}) {
  const language = useMemo(
    () => (fileName ? detectLanguageFromPath(fileName) : 'plaintext'),
    [fileName]
  );

  const tokens = usePrismTokens({code: line.value, language});

  // If we have changes (diff), use the CodeDiff component
  if (line.changes) {
    return (
      <Fragment>
        {line.changes.map((change, i) => (
          <CodeDiff key={i} added={change.added} removed={change.removed}>
            {change.value}
          </CodeDiff>
        ))}
      </Fragment>
    );
  }

  // For non-changed lines, apply syntax highlighting
  return (
    <SyntaxHighlightedCode>
      <pre className={`language-${language}`}>
        <code>
          {tokens.map((lineTokens, i) => (
            <Fragment key={i}>
              {lineTokens.map((token, j) => (
                <span key={j} className={token.className}>
                  {token.children}
                </span>
              ))}
            </Fragment>
          ))}
        </code>
      </pre>
    </SyntaxHighlightedCode>
  );
}

function HunkHeader({lines, sectionHeader}: {lines: DiffLine[]; sectionHeader: string}) {
  const {sourceStart, sourceLength, targetStart, targetLength} = useMemo(
    () => ({
      sourceStart: lines.at(0)?.source_line_no ?? 0,
      sourceLength: lines.filter(line => line.line_type !== DiffLineType.ADDED).length,
      targetStart: lines.at(0)?.target_line_no ?? 0,
      targetLength: lines.filter(line => line.line_type !== DiffLineType.REMOVED).length,
    }),
    [lines]
  );

  return (
    <HunkHeaderContent>{`@@ -${sourceStart},${sourceLength} +${targetStart},${targetLength} @@ ${sectionHeader ? ' ' + sectionHeader : ''}`}</HunkHeaderContent>
  );
}

function useUpdateHunk({groupId, runId}: {groupId: string; runId: string}) {
  const api = useApi({persistInFlight: true});
  const queryClient = useQueryClient();
  const orgSlug = useOrganization().slug;

  return useMutation({
    mutationFn: (params: {
      fileName: string;
      hunkIndex: number;
      lines: DiffLine[];
      repoId?: string;
    }) => {
      return api.requestPromise(
        `/organizations/${orgSlug}/issues/${groupId}/autofix/update/`,
        {
          method: 'POST',
          data: {
            run_id: runId,
            payload: {
              type: 'update_code_change',
              repo_id: params.repoId ?? null,
              hunk_index: params.hunkIndex,
              lines: params.lines,
              file_path: params.fileName,
            },
          },
        }
      );
    },
    onSuccess: _ => {
      queryClient.invalidateQueries({
        queryKey: makeAutofixQueryKey(orgSlug, groupId, true),
      });
      queryClient.invalidateQueries({
        queryKey: makeAutofixQueryKey(orgSlug, groupId, false),
      });
    },
    onError: () => {
      addErrorMessage(t('Something went wrong when updating changes.'));
    },
  });
}

function DiffHunkContent({
  groupId,
  runId,
  repoId,
  hunkIndex,
  lines,
  header,
  fileName,
  editable,
}: {
  editable: boolean;
  fileName: string;
  groupId: string;
  header: string;
  hunkIndex: number;
  lines: DiffLine[];
  runId: string;
  repoId?: string;
}) {
  const [linesWithChanges, setLinesWithChanges] = useState<DiffLineWithChanges[]>([]);

  useEffect(() => {
    setLinesWithChanges(addChangesToDiffLines(lines));
  }, [lines]);

  const [editingGroup, setEditingGroup] = useState<number | null>(null);
  const [editedContent, setEditedContent] = useState<string>('');
  const [editedLines, setEditedLines] = useState<string[]>([]);
  const overlayRef = useRef<HTMLDivElement>(null);
  const [hoveredGroup, setHoveredGroup] = useState<number | null>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (overlayRef.current && !overlayRef.current.contains(event.target as Node)) {
        setEditingGroup(null);
        setEditedContent('');
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [overlayRef]);

  const lineGroups = useMemo(() => {
    const groups: Array<{end: number; start: number; type: 'change' | DiffLineType}> = [];
    let currentGroup: (typeof groups)[number] | null = null;

    linesWithChanges.forEach((line, index) => {
      if (line.line_type !== DiffLineType.CONTEXT) {
        if (!currentGroup) {
          currentGroup = {start: index, end: index, type: 'change'};
        } else if (currentGroup.type === 'change') {
          currentGroup.end = index;
        } else {
          groups.push(currentGroup);
          currentGroup = {start: index, end: index, type: 'change'};
        }
      } else if (currentGroup) {
        groups.push(currentGroup);
        currentGroup = null;
      }
    });

    if (currentGroup) {
      groups.push(currentGroup);
    }

    return groups;
  }, [linesWithChanges]);

  const handleEditClick = (index: number) => {
    const group = lineGroups.find(g => g.start === index);
    if (group) {
      const content = linesWithChanges
        .slice(group.start, group.end + 1)
        .filter(line => line.line_type === DiffLineType.ADDED)
        .map(line => line.value)
        .join('');
      const splitLines = content.split('\n');
      if (splitLines[splitLines.length - 1] === '') {
        splitLines.pop();
      }
      setEditedLines(splitLines);
      if (content === '\n') {
        setEditedContent('');
      } else {
        setEditedContent(content.endsWith('\n') ? content.slice(0, -1) : content);
      }
      setEditingGroup(index);
    }
  };

  const handleTextAreaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newContent = e.target.value;
    setEditedContent(newContent);
    setEditedLines(newContent.split('\n'));
  };

  const updateHunk = useUpdateHunk({groupId, runId});
  const handleSaveEdit = () => {
    if (editingGroup === null) {
      return;
    }
    const group = lineGroups.find(g => g.start === editingGroup);
    if (!group) {
      return;
    }

    let lastSourceLineNo = 0;
    let lastTargetLineNo = 0;
    let lastDiffLineNo = 0;

    const updatedLines = linesWithChanges
      .map((line, index) => {
        if (index < group.start) {
          lastSourceLineNo = line.source_line_no ?? lastSourceLineNo;
          lastTargetLineNo = line.target_line_no ?? lastTargetLineNo;
          lastDiffLineNo = line.diff_line_no ?? lastDiffLineNo;
        }
        if (index >= group.start && index <= group.end) {
          if (line.line_type === DiffLineType.ADDED) {
            return null; // Remove existing added lines
          }
          if (line.line_type === DiffLineType.REMOVED) {
            lastSourceLineNo = line.source_line_no ?? lastSourceLineNo;
          }
          return line; // Keep other lines (removed and context) as is
        }
        return line;
      })
      .filter((line): line is DiffLine => line !== null);

    // Insert new added lines
    const newAddedLines: DiffLine[] = editedContent.split('\n').map((content, i) => {
      lastDiffLineNo++;
      lastTargetLineNo++;
      return {
        diff_line_no: lastDiffLineNo,
        source_line_no: null,
        target_line_no: lastTargetLineNo,
        line_type: DiffLineType.ADDED,
        value: content + (i === editedContent.split('\n').length - 1 ? '' : '\n'),
      };
    });

    // Find the insertion point (after the last removed line or at the start of the group)
    const insertionIndex = updatedLines.findIndex(
      (line, index) => index >= group.start && line.line_type !== DiffLineType.REMOVED
    );

    updatedLines.splice(
      insertionIndex === -1 ? group.start : insertionIndex,
      0,
      ...newAddedLines
    );

    // Update diff_line_no for all lines after the insertion
    for (let i = insertionIndex + newAddedLines.length; i < updatedLines.length; i++) {
      updatedLines[i]!.diff_line_no = ++lastDiffLineNo;
    }

    updateHunk.mutate({hunkIndex, lines: updatedLines, repoId, fileName});
    setLinesWithChanges(addChangesToDiffLines(updatedLines));
    setEditingGroup(null);
    setEditedContent('');
  };

  const handleCancelEdit = () => {
    setEditingGroup(null);
    setEditedContent('');
  };

  const rejectChanges = (index: number) => {
    const group = lineGroups.find(g => g.start === index);
    if (!group) {
      return;
    }

    const updatedLines = linesWithChanges
      .map((line, i) => {
        if (i >= group.start && i <= group.end) {
          if (line.line_type === DiffLineType.ADDED) {
            return null; // Remove added lines
          }
          if (line.line_type === DiffLineType.REMOVED) {
            return {...line, line_type: DiffLineType.CONTEXT}; // Convert removed lines to context
          }
        }
        return line;
      })
      .filter((line): line is DiffLine => line !== null);

    updateHunk.mutate({hunkIndex, lines: updatedLines, repoId, fileName});
    setLinesWithChanges(addChangesToDiffLines(updatedLines));
  };

  const getStartLineNumber = (index: number, lineType: DiffLineType) => {
    const line = linesWithChanges[index]!;
    if (lineType === DiffLineType.REMOVED) {
      return line.source_line_no;
    }
    if (lineType === DiffLineType.ADDED) {
      // Find the first non-null target_line_no
      for (let i = index; i < linesWithChanges.length; i++) {
        if (linesWithChanges[i]!.target_line_no !== null) {
          return linesWithChanges[i]!.target_line_no;
        }
      }
    }
    return null;
  };

  const handleClearChanges = () => {
    setEditedContent('');
    setEditedLines([]);
  };

  const getDeletedLineTitle = (index: number) => {
    return t(
      '%s deleted line%s%s',
      linesWithChanges
        .slice(index, lineGroups.find(g => g.start === index)?.end! + 1)
        .filter(l => l.line_type === DiffLineType.REMOVED).length,
      linesWithChanges
        .slice(index, lineGroups.find(g => g.start === index)?.end)
        .filter(l => l.line_type === DiffLineType.REMOVED).length === 1
        ? ''
        : 's',
      linesWithChanges
        .slice(index, lineGroups.find(g => g.start === index)?.end)
        .some(l => l.line_type === DiffLineType.REMOVED)
        ? t(' from line %s', getStartLineNumber(index, DiffLineType.REMOVED))
        : ''
    );
  };

  const getNewLineTitle = (index: number) => {
    return t(
      '%s new line%s%s',
      editedLines.length,
      editedLines.length === 1 ? '' : 's',
      editedLines.length > 0
        ? t(' from line %s', getStartLineNumber(index, DiffLineType.ADDED))
        : ''
    );
  };

  return (
    <Fragment>
      <HunkHeaderEmptySpace />
      <HunkHeader lines={lines} sectionHeader={header} />
      {linesWithChanges.map((line, index) => (
        <Fragment key={`${line.diff_line_no}-${index}`}>
          <LineNumber lineType={line.line_type}>{line.source_line_no}</LineNumber>
          <LineNumber lineType={line.line_type}>{line.target_line_no}</LineNumber>
          <DiffContent
            lineType={line.line_type}
            data-test-id={makeTestIdFromLineType(line.line_type)}
            onMouseEnter={() => {
              const group = lineGroups.find(g => index >= g.start && index <= g.end);
              if (group) {
                setHoveredGroup(group.start);
              }
            }}
            onMouseLeave={() => setHoveredGroup(null)}
          >
            <DiffLineCode line={line} fileName={fileName} />
            {editable && lineGroups.some(group => index === group.start) && (
              <ButtonGroup data-ignore-autofix-highlight="true">
                <ActionButton
                  size="xs"
                  icon={<IconEdit size="xs" />}
                  aria-label={t('Edit changes')}
                  title={t('Edit')}
                  onClick={() => handleEditClick(index)}
                  isHovered={hoveredGroup === index}
                />
                <ActionButton
                  size="xs"
                  icon={<IconClose size="xs" />}
                  aria-label={t('Reject changes')}
                  title={t('Reject')}
                  onClick={() => rejectChanges(index)}
                  isHovered={hoveredGroup === index}
                />
              </ButtonGroup>
            )}
          </DiffContent>
        </Fragment>
      ))}
      {editingGroup !== null &&
        document.body &&
        createPortal(
          <EditOverlay
            ref={overlayRef}
            data-ignore-autofix-highlight="true"
            data-overlay="true"
          >
            <OverlayHeader>
              <OverlayTitle>
                {t('Editing')} <code>{fileName}</code>
              </OverlayTitle>
            </OverlayHeader>
            <OverlayContent>
              <SectionTitle>{getDeletedLineTitle(editingGroup)}</SectionTitle>
              {linesWithChanges
                .slice(
                  editingGroup,
                  lineGroups.find(g => g.start === editingGroup)?.end! + 1
                )
                .some(l => l.line_type === DiffLineType.REMOVED) ? (
                <RemovedLines>
                  {linesWithChanges
                    .slice(
                      editingGroup,
                      lineGroups.find(g => g.start === editingGroup)?.end! + 1
                    )
                    .filter(l => l.line_type === DiffLineType.REMOVED)
                    .map((l, i) => (
                      <RemovedLine key={i}>{l.value}</RemovedLine>
                    ))}
                </RemovedLines>
              ) : (
                <NoChangesMessage>{t('No lines are being deleted.')}</NoChangesMessage>
              )}
              <SectionTitle>{getNewLineTitle(editingGroup)}</SectionTitle>
              <TextAreaWrapper>
                <StyledTextArea
                  value={editedContent}
                  onChange={handleTextAreaChange}
                  rows={5}
                  autosize
                  placeholder={
                    editedLines.length === 0 ? t('No lines are being added...') : ''
                  }
                  autoFocus
                />
                <ClearButton
                  size="xs"
                  onClick={handleClearChanges}
                  aria-label={t('Clear changes')}
                  icon={<IconDelete size="xs" />}
                  title={t('Clear all new lines')}
                />
              </TextAreaWrapper>
            </OverlayContent>
            <OverlayFooter>
              <OverlayButtonGroup>
                <Button onClick={handleCancelEdit}>{t('Cancel')}</Button>
                <Button priority="primary" onClick={handleSaveEdit}>
                  {t('Save')}
                </Button>
              </OverlayButtonGroup>
            </OverlayFooter>
          </EditOverlay>,
          document.body
        )}
    </Fragment>
  );
}

function FileDiff({
  file,
  groupId,
  runId,
  repoId,
  editable,
  integratedStyle,
}: {
  editable: boolean;
  file: FilePatch;
  groupId: string;
  integratedStyle: boolean;
  runId: string;
  repoId?: string;
}) {
  const [isExpanded, setIsExpanded] = useState(true);

  const containerRef = useRef<HTMLDivElement>(null);

  return (
    <FileDiffWrapper integratedStyle={integratedStyle}>
      {!integratedStyle && (
        <FileHeader onClick={() => setIsExpanded(value => !value)}>
          <InteractionStateLayer />
          <FileAddedRemoved>
            <FileAdded>+{file.added}</FileAdded>
            <FileRemoved>-{file.removed}</FileRemoved>
          </FileAddedRemoved>
          <FileName title={file.path}>{file.path}</FileName>
          <Button
            icon={<IconChevron size="xs" direction={isExpanded ? 'up' : 'down'} />}
            aria-label={t('Toggle file diff')}
            aria-expanded={isExpanded}
            size="zero"
            borderless
          />
        </FileHeader>
      )}
      {integratedStyle && (
        <FileHeader>
          <FileAddedRemoved>
            <FileAdded>+{file.added}</FileAdded>
            <FileRemoved>-{file.removed}</FileRemoved>
          </FileAddedRemoved>
          <FileName title={file.path}>{file.path}</FileName>
        </FileHeader>
      )}
      {isExpanded && (
        <DiffContainer ref={containerRef} integratedStyle={integratedStyle}>
          {file.hunks.map(({section_header, source_start, lines}, index) => {
            return (
              <DiffHunkContent
                key={source_start}
                repoId={repoId}
                groupId={groupId}
                runId={runId}
                hunkIndex={index}
                lines={lines}
                header={section_header}
                fileName={file.path}
                editable={editable}
              />
            );
          })}
        </DiffContainer>
      )}
    </FileDiffWrapper>
  );
}

export function AutofixDiff({
  diff,
  groupId,
  runId,
  repoId,
  editable,
  previousDefaultStepIndex,
  previousInsightCount,
  integratedStyle = false,
}: AutofixDiffProps) {
  if (!diff?.length) {
    return null;
  }

  return (
    <DiffsColumn>
      {diff.map(file => (
        <AutofixHighlightWrapper
          key={file.path}
          groupId={groupId}
          runId={runId}
          stepIndex={previousDefaultStepIndex ?? 0}
          retainInsightCardIndex={
            previousInsightCount !== undefined && previousInsightCount >= 0
              ? previousInsightCount - 1
              : -1
          }
          displayName={`Diff for ${file.path}`}
        >
          <FileDiff
            file={file}
            groupId={groupId}
            runId={runId}
            repoId={repoId}
            editable={editable}
            integratedStyle={integratedStyle}
          />
        </AutofixHighlightWrapper>
      ))}
    </DiffsColumn>
  );
}

const DiffsColumn = styled('div')`
  display: flex;
  flex-direction: column;
  gap: ${space(1)};
`;

const FileDiffWrapper = styled('div')<{integratedStyle?: boolean}>`
  font-family: ${p => p.theme.text.familyMono};
  font-size: ${p => p.theme.fontSize.sm};
  & code {
    font-size: ${p => (p.integratedStyle ? p.theme.fontSize.sm : p.theme.codeFontSize)};
  }
  line-height: 20px;
  vertical-align: middle;
  border: 1px solid ${p => p.theme.border};
  border-color: ${p => (p.integratedStyle ? 'transparent' : p.theme.border)};
  border-radius: ${p => p.theme.borderRadius};
  overflow: hidden;
  background-color: ${p => p.theme.background};
`;

const FileHeader = styled('div')`
  position: relative;
  display: grid;
  align-items: center;
  grid-template-columns: minmax(60px, auto) 1fr auto;
  gap: ${space(2)};
  background-color: ${p => p.theme.backgroundSecondary};
  padding: ${space(1)} ${space(2)};
  cursor: pointer;
`;

const FileAddedRemoved = styled('div')`
  display: flex;
  gap: ${space(1)};
  align-items: center;
`;

const FileAdded = styled('div')`
  color: ${p => p.theme.successText};
`;

const FileRemoved = styled('div')`
  color: ${p => p.theme.errorText};
`;

const FileName = styled('div')`
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
  direction: rtl;
  text-align: left;
`;

const DiffContainer = styled('div')<{integratedStyle?: boolean}>`
  border-top: ${p => (p.integratedStyle ? 'none' : '1px solid ' + p.theme.innerBorder)};
  display: grid;
  grid-template-columns: auto auto 1fr;
  overflow-x: auto;
`;

const HunkHeaderEmptySpace = styled('div')`
  grid-column: 1 / 3;
  background-color: ${p => p.theme.backgroundSecondary};
`;

const HunkHeaderContent = styled('div')`
  grid-column: 3 / -1;
  background-color: ${p => p.theme.backgroundSecondary};
  color: ${p => p.theme.subText};
  padding: ${space(0.75)} ${space(1)} ${space(0.75)} ${space(4)};
  white-space: pre-wrap;
`;

const LineNumber = styled('div')<{lineType: DiffLineType}>`
  display: flex;
  padding: ${space(0.25)} ${space(1)};
  user-select: none;

  background-color: ${p => p.theme.backgroundSecondary};
  color: ${p => p.theme.subText};

  ${p =>
    p.lineType === DiffLineType.ADDED &&
    `background-color: ${DIFF_COLORS.added}; color: ${p.theme.textColor}`};
  ${p =>
    p.lineType === DiffLineType.REMOVED &&
    `background-color: ${DIFF_COLORS.removed}; color: ${p.theme.textColor}`};

  & + & {
    padding-left: 0;
  }
`;

const DiffContent = styled('div')<{lineType: DiffLineType}>`
  position: relative;
  padding-left: ${space(4)};
  padding-right: ${space(4)};
  white-space: pre-wrap;
  word-break: break-all;
  word-wrap: break-word;
  overflow: visible;

  ${p =>
    p.lineType === DiffLineType.ADDED &&
    `background-color: ${DIFF_COLORS.addedRow}; color: ${p.theme.textColor}`};
  ${p =>
    p.lineType === DiffLineType.REMOVED &&
    `background-color: ${DIFF_COLORS.removedRow}; color: ${p.theme.textColor}`};

  &::before {
    content: ${p =>
      p.lineType === DiffLineType.ADDED
        ? "'+'"
        : p.lineType === DiffLineType.REMOVED
          ? "'-'"
          : "''"};
    position: absolute;
    top: 1px;
    left: ${space(1)};
  }
`;

const CodeDiff = styled('span')<{added?: boolean; removed?: boolean}>`
  vertical-align: middle;
  ${p => p.added && `background-color: ${DIFF_COLORS.added};`};
  ${p => p.removed && `background-color: ${DIFF_COLORS.removed};`};
`;

const ButtonGroup = styled('div')`
  position: absolute;
  top: 0;
  right: ${space(0.5)};
  display: flex;
`;

const ActionButton = styled(Button)<{isHovered: boolean}>`
  margin-left: ${space(0.5)};
  font-family: ${p => p.theme.text.family};
  background-color: ${p =>
    p.isHovered ? p.theme.button.default.background : p.theme.background};
  color: ${p => (p.isHovered ? p.theme.pink400 : p.theme.textColor)};
  transition:
    background-color 0.2s ease-in-out,
    color 0.2s ease-in-out;

  &:hover {
    background-color: ${p => p.theme.pink400}10;
    color: ${p => p.theme.pink400};
  }
`;

const EditOverlay = styled('div')`
  position: fixed;
  bottom: ${space(2)};
  left: 50%;
  right: ${space(2)};
  background: ${p => p.theme.backgroundElevated};
  border: 1px solid ${p => p.theme.border};
  border-radius: ${p => p.theme.borderRadius};
  box-shadow: ${p => p.theme.dropShadowHeavy};
  z-index: ${p => p.theme.zIndex.tooltip};
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 18rem);

  @media (max-width: ${p => p.theme.breakpoints.sm}) {
    left: ${space(2)};
  }
`;

const OverlayHeader = styled('div')`
  padding: ${space(2)} ${space(2)} 0;
  border-bottom: 1px solid ${p => p.theme.border};
`;

const OverlayContent = styled('div')`
  padding: 0 ${space(2)} ${space(2)} ${space(2)};
  overflow-y: auto;
`;

const OverlayFooter = styled('div')`
  padding: ${space(1)};
  border-top: 1px solid ${p => p.theme.border};
`;

const OverlayButtonGroup = styled('div')`
  display: flex;
  justify-content: flex-end;
  gap: ${space(1)};
  font-family: ${p => p.theme.text.family};
`;

const RemovedLines = styled('div')`
  margin-bottom: ${space(1)};
  font-family: ${p => p.theme.text.familyMono};
  border-radius: ${p => p.theme.borderRadius};
  overflow: hidden;
`;

const RemovedLine = styled('div')`
  background-color: ${DIFF_COLORS.removedRow};
  color: ${p => p.theme.textColor};
  padding: ${space(0.25)} ${space(0.5)};
  white-space: pre-wrap;
`;

const StyledTextArea = styled(TextArea)`
  font-family: ${p => p.theme.text.familyMono};
  background-color: ${DIFF_COLORS.addedRow};
  border-color: ${p => p.theme.border};
  position: relative;
  min-height: 250px;

  &:focus {
    border-color: ${p => p.theme.focusBorder};
    box-shadow: inset 0 0 0 1px ${p => p.theme.focusBorder};
  }
`;

const ClearButton = styled(Button)`
  position: absolute;
  top: -${space(1)};
  right: -${space(1)};
  z-index: 1;
`;

const TextAreaWrapper = styled('div')`
  position: relative;
`;

const SectionTitle = styled('p')`
  margin: ${space(1)} 0;
  font-size: ${p => p.theme.fontSize.md};
  font-weight: bold;
  color: ${p => p.theme.textColor};
  font-family: ${p => p.theme.text.family};
`;

const NoChangesMessage = styled('p')`
  margin: ${space(1)} 0;
  color: ${p => p.theme.subText};
  font-family: ${p => p.theme.text.family};
`;

const OverlayTitle = styled('h3')`
  margin: 0 0 ${space(2)} 0;
  font-size: ${p => p.theme.fontSize.md};
  font-weight: bold;
  color: ${p => p.theme.textColor};
  font-family: ${p => p.theme.text.family};
`;
