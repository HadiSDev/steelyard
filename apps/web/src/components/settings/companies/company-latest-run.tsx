import { useQuery } from '@tanstack/react-query'
import { Bot, Loader2 } from 'lucide-react'
import { Badge } from '#/components/ui'
import { useApi } from '#/lib/auth/auth'
import { companyRunsQueryOptions, isRunInFlight } from '#/lib/api/pipeline-runs'
import type { PipelineRunRead } from '#/lib/api/types'
import { formatRelativeTime } from '#/lib/format/format'
import {
  RUN_KIND_LABELS,
  RUN_STATUS_LABELS,
  RUN_STATUS_VARIANTS,
  SYSTEM_REQUESTER,
  summaryCounts,
} from './run-labels'

export interface CompanyLatestRunProps {
  companyId: string
}

/** The compact line under a company's name describing its latest pipeline run. */
export function CompanyLatestRun({ companyId }: CompanyLatestRunProps) {
  const api = useApi()
  const runs = useQuery(companyRunsQueryOptions(api, companyId))

  if (runs.isPending || runs.isError) {
    return null
  }
  if (runs.data.length === 0) {
    return (
      <p className="mt-1 text-xs font-normal text-muted-foreground">
        No pipeline runs yet
      </p>
    )
  }
  return <LatestRunLine run={runs.data[0]} />
}

/** Kind, status, when it was asked for, and how it ended. */
function LatestRunLine({ run }: { run: PipelineRunRead }) {
  const counts = isRunInFlight(run) ? [] : summaryCounts(run.summary)
  return (
    <div
      role="group"
      className="mt-1.5 flex flex-col gap-1 text-xs font-normal"
      aria-label="Latest pipeline run"
    >
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-semibold text-foreground">
          {RUN_KIND_LABELS[run.kind]}
        </span>
        <Badge variant={RUN_STATUS_VARIANTS[run.status]}>
          {isRunInFlight(run) ? <Loader2 className="animate-spin" /> : null}
          {RUN_STATUS_LABELS[run.status]}
        </Badge>
        <time
          dateTime={run.requested_at}
          title={new Date(run.requested_at).toLocaleString('en-GB')}
          className="text-muted-foreground"
        >
          {formatRelativeTime(run.requested_at)}
        </time>
        {run.requested_by === SYSTEM_REQUESTER ? (
          <span className="inline-flex items-center gap-1 text-muted-foreground">
            <Bot className="size-3" />
            Automatic
          </span>
        ) : null}
      </div>
      {counts.length > 0 ? (
        <p className="text-muted-foreground tabular-nums">
          {counts.join(' · ')}
        </p>
      ) : null}
      {run.status === 'failed' && run.error ? (
        <p className="line-clamp-2 max-w-md text-destructive" title={run.error}>
          {run.error}
        </p>
      ) : null}
    </div>
  )
}
