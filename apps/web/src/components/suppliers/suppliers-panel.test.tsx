import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react'
import type { CompanyRead, Page, VendorOverviewRead } from '#/lib/api/types'
import { SuppliersPanel } from './suppliers-panel'
import type { SuppliersPanelProps } from './suppliers-panel'
import { SEARCH_DELAY_MS } from './suppliers-toolbar'

const ACME: CompanyRead = {
  id: 'c1',
  name: 'Acme A/S',
  country_code: 'DK',
  vat_number: 'DK12345678',
  base_currency: 'DKK',
  is_active: true,
  deactivated_at: null,
  spend_tree_id: null,
  spend_tree_name: null,
}

function supplier(
  overrides: Partial<VendorOverviewRead> = {},
): VendorOverviewRead {
  return {
    id: 'v1',
    name: 'Google Cloud EMEA Limited',
    country_code: 'IE',
    vat_number: 'IE6388047V',
    description: 'Cloud computing and hosting services',
    website: 'https://cloud.google.com/',
    invoice_count: 12,
    last_invoice_date: '2026-09-18',
    spend: [{ currency: 'DKK', amount: '2400.00', unconverted_count: 0 }],
    ...overrides,
  }
}

function page(items: Array<VendorOverviewRead>): Page<VendorOverviewRead> {
  return { items, page: 1, page_size: 25, total: items.length }
}

function setup(overrides: Partial<SuppliersPanelProps> = {}) {
  const props: SuppliersPanelProps = {
    result: page([supplier()]),
    loading: false,
    error: false,
    filters: {},
    sort: 'spend',
    order: 'desc',
    spendSortable: true,
    companies: [ACME],
    onFiltersChange: vi.fn(),
    onClearFilters: vi.fn(),
    onSort: vi.fn(),
    onPageChange: vi.fn(),
    onSelect: vi.fn(),
    ...overrides,
  }
  render(<SuppliersPanel {...props} />)
  return props
}

function row(name: string): HTMLElement {
  const button = screen.getByRole('button', {
    name: `View details for ${name}`,
  })
  const found = button.closest('tr')
  if (found === null) {
    throw new Error(`no row for ${name}`)
  }
  return found
}

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('SuppliersPanel — the table', () => {
  it('shows each supplier with its figures', () => {
    setup()

    const cells = within(row('Google Cloud EMEA Limited'))
    expect(cells.getByText('Ireland')).toBeTruthy()
    expect(cells.getByText('IE6388047V')).toBeTruthy()
    expect(cells.getByText('Cloud computing and hosting services')).toBeTruthy()
    expect(cells.getByText('12')).toBeTruthy()
    expect(cells.getByText(/DKK\s2,400\.00/)).toBeTruthy()
    expect(cells.getByText('18 Sept 2026')).toBeTruthy()
  })

  it('marks a supplier nobody has described', () => {
    setup({ result: page([supplier({ description: null })]) })

    expect(
      within(row('Google Cloud EMEA Limited')).getByText('Not described'),
    ).toBeTruthy()
  })

  it('marks a missing country, VAT number and date rather than leaving them blank', () => {
    setup({
      result: page([
        supplier({
          country_code: null,
          vat_number: null,
          last_invoice_date: null,
        }),
      ]),
    })

    expect(
      within(row('Google Cloud EMEA Limited')).getAllByText('—'),
    ).toHaveLength(3)
  })

  it('shows the country with its flag in a column of its own', () => {
    setup()

    const table = screen.getByRole('table')
    const headers = within(table)
      .getAllByRole('columnheader')
      .map((header) => header.textContent)
    const cell = screen.getByText('Ireland').closest('td')
    expect(headers[1]).toBe('Country')
    expect(cell?.querySelector('img')).not.toBeNull()
  })

  it('falls back to the code for a country it cannot name', () => {
    setup({ result: page([supplier({ country_code: 'xk' })]) })

    expect(
      within(row('Google Cloud EMEA Limited')).getByText('XK'),
    ).toBeTruthy()
  })

  it('shows each currency’s spend apart', () => {
    setup({
      result: page([
        supplier({
          spend: [
            { currency: 'DKK', amount: '2400.00', unconverted_count: 0 },
            { currency: 'EUR', amount: '310.00', unconverted_count: 0 },
          ],
        }),
      ]),
    })

    const cells = within(row('Google Cloud EMEA Limited'))
    expect(cells.getByText(/DKK\s2,400\.00/)).toBeTruthy()
    expect(cells.getByText('€310.00')).toBeTruthy()
  })

  it('says how many invoices could not be converted', () => {
    setup({
      result: page([
        supplier({
          spend: [{ currency: 'DKK', amount: '0', unconverted_count: 2 }],
        }),
      ]),
    })

    expect(screen.getByText('2 not converted')).toBeTruthy()
  })

  it('offers the full description to the keyboard', () => {
    setup()

    const description = screen.getByText('Cloud computing and hosting services')
    expect(description.getAttribute('tabindex')).toBe('0')
  })

  it('fixes its column widths, so sorting or paging cannot reflow it', () => {
    setup()

    const table = screen.getByRole('table')
    expect(table.className).toContain('table-fixed')
    expect(table.querySelectorAll('colgroup > col')).toHaveLength(
      within(table).getAllByRole('columnheader').length,
    )
  })
})

describe('SuppliersPanel — sorting', () => {
  it('marks the column the table is sorted by', () => {
    setup({ sort: 'spend', order: 'desc' })

    const spend = screen.getByRole('columnheader', { name: /Spend/ })
    expect(spend.getAttribute('aria-sort')).toBe('descending')
    expect(
      screen
        .getByRole('columnheader', { name: /Supplier/ })
        .getAttribute('aria-sort'),
    ).toBe('none')
  })

  it('asks to sort by a column when its header is pressed', () => {
    const props = setup()

    fireEvent.click(screen.getByRole('button', { name: /Invoices/ }))

    expect(props.onSort).toHaveBeenCalledWith('invoice_count')
  })

  it('offers no spend sorting when it would compare currencies', () => {
    setup({ sort: 'name', order: 'asc', spendSortable: false })

    const spend = screen.getByRole('columnheader', { name: 'Spend' })
    expect(within(spend).queryByRole('button')).toBeNull()
    expect(spend.getAttribute('aria-sort')).toBeNull()
  })
})

describe('SuppliersPanel — search and filters', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it('searches once the user pauses typing', () => {
    const props = setup()

    fireEvent.change(screen.getByRole('searchbox'), {
      target: { value: 'google' },
    })
    expect(props.onFiltersChange).not.toHaveBeenCalled()

    act(() => {
      vi.advanceTimersByTime(SEARCH_DELAY_MS)
    })
    expect(props.onFiltersChange).toHaveBeenCalledWith({ q: 'google' })
  })

  it('shows the search it was opened with', () => {
    setup({ filters: { q: 'google' } })

    expect(screen.getByDisplayValue('google')).toBe(
      screen.getByRole('searchbox'),
    )
  })
})

describe('SuppliersPanel — choosing a supplier', () => {
  it('opens a supplier from its row', () => {
    const props = setup()

    fireEvent.click(row('Google Cloud EMEA Limited'))

    expect(props.onSelect).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'v1' }),
    )
  })

  it('opens them from the keyboard too', () => {
    const props = setup()

    const button = screen.getByRole('button', {
      name: 'View details for Google Cloud EMEA Limited',
    })
    button.focus()
    fireEvent.click(button)

    expect(props.onSelect).toHaveBeenCalledTimes(1)
  })
})

describe('SuppliersPanel — states', () => {
  it('holds the table’s place while loading', () => {
    setup({ loading: true, result: undefined })

    expect(screen.getByTestId('suppliers-loading')).toBeTruthy()
  })

  it('explains where suppliers come from before any are synced', () => {
    setup({ result: page([]) })

    expect(screen.getByText('No suppliers yet')).toBeTruthy()
    expect(screen.getByText(/once invoices are synced/)).toBeTruthy()
  })

  it('offers to clear a search that matches nothing', () => {
    const props = setup({ result: page([]), filters: { q: 'zzz' } })

    expect(screen.getByText('No suppliers match')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))
    expect(props.onClearFilters).toHaveBeenCalled()
  })

  it('shows an error instead of an empty table', () => {
    setup({ error: true, result: undefined })

    expect(screen.getByText('Couldn’t load your suppliers')).toBeTruthy()
    expect(screen.queryByRole('table')).toBeNull()
  })

  it('counts every supplier and pages through them', () => {
    const props = setup({
      result: { items: [supplier()], page: 1, page_size: 25, total: 60 },
    })

    expect(screen.getByText('60 suppliers')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /next/i }))
    expect(props.onPageChange).toHaveBeenCalledWith(2)
  })
})
