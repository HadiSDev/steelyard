import type { BadgeProps } from '#/components/ui'
import { isRunInFlight } from '#/lib/api/pipeline-runs'
import type {
  PipelineRunKind,
  PipelineRunRead,
  PipelineRunStatus,
} from '#/lib/api/types'
import { formatCount, humanizeKey } from '#/lib/format/format'

/** The run kinds in the order the Run menu offers them. */
export const RUN_KINDS: ReadonlyArray<PipelineRunKind> = [
  'sync',
  'read_documents',
  'categorize',
]

/** What each run kind is called in the UI. */
export const RUN_KIND_LABELS: Record<PipelineRunKind, string> = {
  sync: 'Sync from ERP',
  read_documents: 'Read documents',
  categorize: 'Categorize lines',
}

/** What each run status is called in the UI. */
export const RUN_STATUS_LABELS: Record<PipelineRunStatus, string> = {
  queued: 'Queued',
  running: 'Running',
  succeeded: 'Succeeded',
  failed: 'Failed',
}

/** The badge colour for each run status. */
export const RUN_STATUS_VARIANTS: Record<
  PipelineRunStatus,
  NonNullable<BadgeProps['variant']>
> = {
  queued: 'info',
  running: 'warning',
  succeeded: 'success',
  failed: 'destructive',
}

/** The `requested_by` value of a run the worker started on its own. */
export const SYSTEM_REQUESTER = 'system'

/** How many counts the latest-run line shows at most. */
const MAX_SUMMARY_COUNTS = 3

/** The status of each kind that has a run queued or running. */
export function inFlightKinds(
  runs: ReadonlyArray<PipelineRunRead>,
): Map<PipelineRunKind, PipelineRunStatus> {
  const kinds = new Map<PipelineRunKind, PipelineRunStatus>()
  for (const run of runs) {
    if (isRunInFlight(run) && !kinds.has(run.kind)) {
      kinds.set(run.kind, run.status)
    }
  }
  return kinds
}

/** Add every number in a summary to `totals`, summing nested records by key. */
function collectCounts(value: unknown, totals: Map<string, number>) {
  if (Array.isArray(value)) {
    for (const item of value) {
      collectCounts(item, totals)
    }
    return
  }
  if (typeof value !== 'object' || value === null) {
    return
  }
  for (const [key, entry] of Object.entries(value)) {
    if (typeof entry === 'number') {
      totals.set(key, (totals.get(key) ?? 0) + entry)
    } else {
      collectCounts(entry, totals)
    }
  }
}

/** A summary key as lower-case words, keeping acronyms such as `AI` intact. */
function countLabel(key: string): string {
  const [first = '', ...rest] = humanizeKey(key).split(' ')
  const isAcronym = first.length > 1 && first === first.toUpperCase()
  const lead = isAcronym ? first : first.toLowerCase()
  return [lead, ...rest].join(' ')
}

/** A run summary's non-zero counts as short phrases, e.g. `["12 categorized", "1 failed"]`. */
export function summaryCounts(
  summary: Record<string, unknown> | null,
): Array<string> {
  const totals = new Map<string, number>()
  collectCounts(summary, totals)
  return [...totals.entries()]
    .filter(([, count]) => count !== 0)
    .slice(0, MAX_SUMMARY_COUNTS)
    .map(([key, count]) => `${formatCount(count)} ${countLabel(key)}`)
}
