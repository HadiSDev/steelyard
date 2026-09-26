import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ToastProvider } from '#/components/ui'
import { ApiError } from '#/lib/api/api-client'
import type { ApiClient } from '#/lib/api/api-client'
import type {
  CompanyRead,
  ErpIntegrationRead,
  PipelineRunKind,
  PipelineRunRead,
} from '#/lib/api/types'
import { CompaniesPanel } from './companies-panel'
import type { CompaniesPanelProps } from './companies-panel'

const get = vi.fn()
const post = vi.fn()

vi.mock('#/lib/auth/auth', () => ({
  useApi: (): ApiClient => ({
    get,
    post,
    patch: vi.fn(),
    del: vi.fn(),
    getBlob: vi.fn(),
  }),
}))

const ACME: CompanyRead = {
  id: 'c1',
  name: 'Acme A/S',
  country_code: 'DK',
  vat_number: 'DK12345678',
  base_currency: 'DKK',
  is_active: true,
  deactivated_at: null,
  spend_tree_id: 'tree1',
  spend_tree_name: 'Default spend tree',
}

const INTEGRATION: ErpIntegrationRead = {
  id: 'i1',
  company_id: 'c1',
  erp_type: 'mock',
  label: 'Main',
  connected_at: '2026-03-01T00:00:00Z',
  disconnected_at: null,
  created_at: '2026-03-01T00:00:00Z',
  has_credentials: true,
}

function makeRun(overrides: Partial<PipelineRunRead> = {}): PipelineRunRead {
  return {
    id: 'r1',
    company_id: 'c1',
    kind: 'categorize',
    status: 'queued',
    requested_by: 'user_1',
    requested_at: new Date().toISOString(),
    started_at: null,
    finished_at: null,
    summary: null,
    error: null,
    ...overrides,
  }
}

/** The runs `GET /companies/c1/runs` answers with. */
let storedRuns: Array<PipelineRunRead> = []

function renderPanel(overrides: Partial<CompaniesPanelProps> = {}) {
  const props: CompaniesPanelProps = {
    companies: [ACME],
    includeInactive: false,
    onIncludeInactiveChange: vi.fn(),
    canManage: true,
    canRunPipelines: true,
    integrations: [INTEGRATION],
    onCreate: vi.fn().mockResolvedValue(undefined),
    onUpdate: vi.fn().mockResolvedValue(undefined),
    onSetActive: vi.fn().mockResolvedValue(undefined),
    onDelete: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  }
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <CompaniesPanel {...props} />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

async function openRunMenu() {
  fireEvent.click(
    await screen.findByRole('button', { name: 'Run pipeline for Acme A/S' }),
  )
}

beforeEach(() => {
  storedRuns = []
  get.mockImplementation(() => Promise.resolve(storedRuns))
  post.mockImplementation((_path: string, body: { kind: PipelineRunKind }) => {
    const run = makeRun({ id: 'new', kind: body.kind })
    storedRuns = [run, ...storedRuns]
    return Promise.resolve(run)
  })
})

afterEach(() => {
  vi.clearAllMocks()
})

describe('CompaniesPanel — pipeline runs for everyone else', () => {
  it('renders no Run menu and no run status, and asks for no runs', async () => {
    renderPanel({ canRunPipelines: false })

    await screen.findByRole('button', { name: 'Actions for Acme A/S' })

    expect(
      screen.queryByRole('button', { name: 'Run pipeline for Acme A/S' }),
    ).toBeNull()
    expect(
      screen.queryByRole('group', { name: 'Latest pipeline run' }),
    ).toBeNull()
    expect(screen.queryByText('No pipeline runs yet')).toBeNull()
    expect(get).not.toHaveBeenCalled()
  })
})

describe('CompaniesPanel — pipeline runs for a system admin', () => {
  it('offers the three actions on the company row', async () => {
    renderPanel()

    await openRunMenu()

    expect(
      await screen.findByRole('menuitem', { name: 'Sync from ERP' }),
    ).toBeTruthy()
    expect(
      screen.getByRole('menuitem', { name: 'Read documents' }),
    ).toBeTruthy()
    expect(
      screen.getByRole('menuitem', { name: 'Categorize lines' }),
    ).toBeTruthy()
    expect(get).toHaveBeenCalledWith('/api/v1/companies/c1/runs', {
      limit: 20,
    })
  })

  it.each([
    ['Sync from ERP', 'sync'],
    ['Read documents', 'read_documents'],
    ['Categorize lines', 'categorize'],
  ] as const)('%s requests a %s run', async (label, kind) => {
    renderPanel()

    await openRunMenu()
    fireEvent.click(await screen.findByRole('menuitem', { name: label }))

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith('/api/v1/companies/c1/runs', { kind }),
    )
    expect(await screen.findByText(`${label} queued`)).toBeTruthy()
  })

  it('shows a requested run as queued without a reload', async () => {
    renderPanel()

    expect(await screen.findByText('No pipeline runs yet')).toBeTruthy()
    await openRunMenu()
    fireEvent.click(
      await screen.findByRole('menuitem', { name: 'Categorize lines' }),
    )

    const line = await screen.findByRole('group', {
      name: 'Latest pipeline run',
    })
    expect(line.textContent).toContain('Categorize lines')
    expect(line.textContent).toContain('Queued')
  })

  it('shows a refusal from the server as an error', async () => {
    post.mockRejectedValue(
      new ApiError(409, 'Request failed with 409', {
        detail: 'This company has no connected ERP integration.',
      }),
    )
    renderPanel()

    await openRunMenu()
    fireEvent.click(
      await screen.findByRole('menuitem', { name: 'Sync from ERP' }),
    )

    expect(await screen.findByText('Sync from ERP not started')).toBeTruthy()
    expect(
      screen.getByText('This company has no connected ERP integration.'),
    ).toBeTruthy()
  })

  it('shows an in-progress action as such and does not offer it again', async () => {
    storedRuns = [makeRun({ kind: 'read_documents', status: 'running' })]
    renderPanel()

    await screen.findByRole('group', { name: 'Latest pipeline run' })
    await openRunMenu()

    const busy = await screen.findByRole('menuitem', {
      name: /Read documents/,
    })
    expect(busy.getAttribute('aria-disabled')).toBe('true')
    expect(busy.textContent).toContain('Running…')
    fireEvent.click(busy)
    expect(post).not.toHaveBeenCalled()

    const idle = screen.getByRole('menuitem', { name: 'Categorize lines' })
    expect(idle.getAttribute('aria-disabled')).not.toBe('true')
  })

  it('states the error of a failed run', async () => {
    storedRuns = [
      makeRun({
        kind: 'sync',
        status: 'failed',
        finished_at: new Date().toISOString(),
        error: 'ERP rejected the credentials',
      }),
    ]
    renderPanel()

    const line = await screen.findByRole('group', {
      name: 'Latest pipeline run',
    })
    expect(line.textContent).toContain('Sync from ERP')
    expect(line.textContent).toContain('Failed')
    expect(screen.getByText('ERP rejected the credentials')).toBeTruthy()
  })

  it('shows a finished automatic run with its counts', async () => {
    storedRuns = [
      makeRun({
        kind: 'read_documents',
        status: 'succeeded',
        requested_by: 'system',
        requested_at: new Date(Date.now() - 5 * 60_000).toISOString(),
        finished_at: new Date().toISOString(),
        summary: { processed: 3, failed: 0, categorized: 7 },
      }),
    ]
    renderPanel()

    const line = await screen.findByRole('group', {
      name: 'Latest pipeline run',
    })
    expect(line.textContent).toContain('Succeeded')
    expect(line.textContent).toContain('Automatic')
    expect(line.textContent).toContain('5 minutes ago')
    expect(screen.getByText('3 processed · 7 categorized')).toBeTruthy()
  })

  it('does not offer Sync from ERP without a connected ERP', async () => {
    renderPanel({
      integrations: [
        { ...INTEGRATION, disconnected_at: '2026-04-01T00:00:00Z' },
      ],
    })

    await openRunMenu()

    expect(
      await screen.findByRole('menuitem', { name: 'Read documents' }),
    ).toBeTruthy()
    expect(screen.queryByRole('menuitem', { name: 'Sync from ERP' })).toBeNull()
  })
})
