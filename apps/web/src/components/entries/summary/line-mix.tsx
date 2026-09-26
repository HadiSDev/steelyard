import { cn } from '#/components/ui'
import { formatCount } from '#/lib/format/format'
import type { SpendCoverageRow } from '#/lib/api/types'

interface Segment {
  key: string
  label: string
  count: number
  className: string
}

/** The row's lines split by where their categorization stands, in reading order. */
export function lineSegments(row: SpendCoverageRow): Array<Segment> {
  const confident =
    row.categorized_lines - row.verified_lines - row.needs_review_lines
  return [
    {
      key: 'verified',
      label: 'Verified',
      count: row.verified_lines,
      className: 'bg-success',
    },
    {
      key: 'ai',
      label: 'AI categorized',
      count: confident,
      className: 'bg-info',
    },
    {
      key: 'review',
      label: 'Needs review',
      count: row.needs_review_lines,
      className: 'bg-warning',
    },
    {
      key: 'uncategorized',
      label: 'Uncategorized',
      count: row.uncategorized_lines,
      className: 'bg-muted-foreground/30',
    },
    {
      key: 'failed',
      label: 'Failed',
      count: row.failed_lines,
      className: 'bg-destructive',
    },
  ].filter((segment) => segment.count > 0)
}

/** A segmented bar of the lines' categorization state, with a legend of counts. */
export function LineMix({ row }: { row: SpendCoverageRow }) {
  const segments = lineSegments(row)
  const summary = segments
    .map((segment) => `${segment.label} ${formatCount(segment.count)}`)
    .join(', ')

  return (
    <div className="flex flex-col gap-2">
      <div
        role="img"
        aria-label={`Lines by state: ${summary}`}
        className="flex h-2 w-full gap-0.5 overflow-hidden rounded-full bg-muted"
      >
        {segments.map((segment) => (
          <span
            key={segment.key}
            className={cn('h-full', segment.className)}
            style={{ flexGrow: segment.count }}
          />
        ))}
      </div>
      <ul className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
        {segments.map((segment) => (
          <li key={segment.key} className="inline-flex items-center gap-1.5">
            <span
              aria-hidden="true"
              className={cn('size-2 rounded-full', segment.className)}
            />
            {segment.label}
            <span className="font-medium tabular-nums text-foreground">
              {formatCount(segment.count)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
