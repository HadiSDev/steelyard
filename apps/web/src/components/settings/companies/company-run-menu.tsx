import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ChevronDown,
  FileText,
  Loader2,
  Play,
  RefreshCw,
  Tags,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import {
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
  useToast,
} from '#/components/ui'
import { useApi } from '#/lib/auth/auth'
import {
  companyRunsQueryOptions,
  requestRunMutation,
} from '#/lib/api/pipeline-runs'
import type {
  CompanyRead,
  PipelineRunKind,
  PipelineRunStatus,
} from '#/lib/api/types'
import { serverErrorMessage } from '#/lib/form-errors'
import {
  RUN_KINDS,
  RUN_KIND_LABELS,
  RUN_STATUS_LABELS,
  inFlightKinds,
} from './run-labels'

/** The icon beside each run kind in the menu. */
const RUN_KIND_ICONS: Record<PipelineRunKind, LucideIcon> = {
  sync: RefreshCw,
  read_documents: FileText,
  categorize: Tags,
}

export interface CompanyRunMenuProps {
  company: CompanyRead
  /** Whether the company has a connected ERP integration to sync from. */
  hasErp: boolean
}

/** The system-admin Run menu on a company row: request one pipeline stage. */
export function CompanyRunMenu({ company, hasErp }: CompanyRunMenuProps) {
  const api = useApi()
  const queryClient = useQueryClient()
  const toast = useToast()
  const runs = useQuery(companyRunsQueryOptions(api, company.id))
  const request = useMutation(requestRunMutation(api, queryClient))

  const busyKinds = inFlightKinds(runs.data ?? [])
  if (request.isPending) {
    busyKinds.set(request.variables.kind, 'queued')
  }
  const kinds = RUN_KINDS.filter((kind) => kind !== 'sync' || hasErp)

  async function start(kind: PipelineRunKind) {
    const label = RUN_KIND_LABELS[kind]
    try {
      const run = await request.mutateAsync({ companyId: company.id, kind })
      toast.add({
        title:
          run.status === 'running'
            ? `${label} is already running`
            : `${label} queued`,
        description: company.name,
      })
    } catch (failure) {
      toast.add({
        title: `${label} not started`,
        description: serverErrorMessage(failure),
      })
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button
            variant="secondary"
            size="sm"
            className="h-8 gap-1.5 px-3 shadow-xs"
            aria-label={`Run pipeline for ${company.name}`}
          >
            {busyKinds.size > 0 ? (
              <Loader2 className="animate-spin text-primary" />
            ) : (
              <Play className="text-primary" />
            )}
            Run
            <ChevronDown className="text-muted-foreground" />
          </Button>
        }
      />
      <DropdownMenuContent align="end" className="min-w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Run for {company.name}</DropdownMenuLabel>
          {kinds.map((kind) => (
            <RunMenuItem
              key={kind}
              kind={kind}
              status={busyKinds.get(kind)}
              onSelect={() => void start(kind)}
            />
          ))}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

interface RunMenuItemProps {
  kind: PipelineRunKind
  /** Set while a run of this kind is queued or running. */
  status: PipelineRunStatus | undefined
  onSelect: () => void
}

/** One run kind in the menu, shown as in progress instead of offered while it runs. */
function RunMenuItem({ kind, status, onSelect }: RunMenuItemProps) {
  const Icon = RUN_KIND_ICONS[kind]
  if (status) {
    return (
      <DropdownMenuItem disabled>
        <Loader2 className="animate-spin" />
        <span className="flex-1">{RUN_KIND_LABELS[kind]}</span>
        <span className="text-xs text-muted-foreground">
          {RUN_STATUS_LABELS[status]}…
        </span>
      </DropdownMenuItem>
    )
  }
  return (
    <DropdownMenuItem onClick={onSelect}>
      <Icon />
      {RUN_KIND_LABELS[kind]}
    </DropdownMenuItem>
  )
}
