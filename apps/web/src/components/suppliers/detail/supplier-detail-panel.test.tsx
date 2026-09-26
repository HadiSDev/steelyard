import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react'
import type {
  VendorCategorySpendRead,
  VendorDetailRead,
  VendorInvoiceRead,
} from '#/lib/api/types'
import { SupplierDetailPanel } from './supplier-detail-panel'
import type { SupplierDetailPanelProps } from './supplier-detail-panel'
import { breakdownByCurrency } from './category-breakdown'
import { websiteLabel } from './supplier-header'

function category(
  overrides: Partial<VendorCategorySpendRead> = {},
): VendorCategorySpendRead {
  return {
    category_id: 'cat-cloud',
    category_name: 'Cloud hosting',
    currency: 'DKK',
    amount: '750.00',
    line_count: 3,
    ...overrides,
  }
}

function detail(overrides: Partial<VendorDetailRead> = {}): VendorDetailRead {
  return {
    id: 'v1',
    name: 'Dansk Retursystem A/S',
    country_code: 'DK',
    vat_number: 'DK12345678',
    description: 'Runs the Danish deposit and return system.',
    description_source: 'web',
    website: 'https://www.danskretursystem.dk/',
    invoice_count: 14,
    first_invoice_date: '2025-01-03',
    last_invoice_date: '2026-09-18',
    spend: [{ currency: 'DKK', amount: '1000.00', unconverted_count: 0 }],
    categories: [
      category(),
      category({
        category_id: null,
        category_name: null,
        amount: '250.00',
        line_count: 1,
      }),
    ],
    recent_invoices: [
      {
        id: 'i1',
        invoice_number: 'INV-2041',
        voucher_number: '4821',
        invoice_date: '2026-09-18',
        company_name: 'Acme A/S',
        currency: 'EUR',
        total: '134.00',
        status: 'verified',
      },
    ],
    ...overrides,
  }
}

function setup(overrides: Partial<SupplierDetailPanelProps> = {}) {
  const props: SupplierDetailPanelProps = {
    supplier: detail(),
    loading: false,
    error: false,
    notFound: false,
    onBack: vi.fn(),
    onViewLines: vi.fn(),
    ...overrides,
  }
  render(<SupplierDetailPanel {...props} />)
  return props
}

afterEach(() => {
  cleanup()
})

describe('SupplierDetailPanel — who the supplier is', () => {
  it('names the supplier with its country, VAT number and website', () => {
    setup()

    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe(
      'Dansk Retursystem A/S',
    )
    expect(screen.getByText('Denmark')).toBeTruthy()
    expect(screen.getByText('DK12345678')).toBeTruthy()
    const website = screen.getByRole('link', { name: /danskretursystem\.dk/ })
    expect(website.getAttribute('href')).toBe(
      'https://www.danskretursystem.dk/',
    )
    expect(website.getAttribute('target')).toBe('_blank')
    expect(website.getAttribute('rel')).toContain('noopener')
  })

  it('says what they sell and where that came from', () => {
    setup()

    expect(
      screen.getByText('Runs the Danish deposit and return system.'),
    ).toBeTruthy()
    expect(screen.getByText('Researched from the web')).toBeTruthy()
  })

  it('marks what is not known rather than leaving it blank', () => {
    setup({
      supplier: detail({
        vat_number: null,
        website: null,
        description: null,
        description_source: null,
      }),
    })

    expect(screen.getByText('Not known')).toBeTruthy()
    expect(screen.getByText('Not described yet.')).toBeTruthy()
    expect(screen.queryByText('Researched from the web')).toBeNull()
  })

  it('names a website by its host', () => {
    expect(websiteLabel('https://www.danskretursystem.dk/en/')).toBe(
      'danskretursystem.dk',
    )
    expect(websiteLabel('not a url')).toBe('not a url')
  })
})

describe('SupplierDetailPanel — figures', () => {
  it('shows the spend, invoice count and first and last invoice', () => {
    setup()

    const spend = screen.getByRole('region', { name: 'Spend, net of VAT' })
    expect(within(spend).getByText(/DKK\s1,000\.00/)).toBeTruthy()
    expect(
      within(screen.getByRole('region', { name: 'Invoices' })).getByText('14'),
    ).toBeTruthy()
    expect(screen.getByText('3 Jan 2025')).toBeTruthy()
    expect(
      within(screen.getByRole('region', { name: 'Last invoice' })).getByText(
        '18 Sept 2026',
      ),
    ).toBeTruthy()
  })

  it('says how many invoices could not be converted', () => {
    setup({
      supplier: detail({
        spend: [{ currency: 'DKK', amount: '1000.00', unconverted_count: 2 }],
      }),
    })

    expect(screen.getByText('2 invoices not converted')).toBeTruthy()
  })
})

describe('SupplierDetailPanel — spend by category', () => {
  it('shows each category’s spend and share, uncategorized last', () => {
    setup()

    const items = within(
      screen.getByRole('region', { name: /Spend by category/ }),
    ).getAllByRole('listitem')
    expect(items.map((item) => item.textContent)).toEqual([
      expect.stringMatching(/Cloud hosting.*DKK\s750\.00.*75%.*3 lines/),
      expect.stringMatching(/Not categorized.*DKK\s250\.00.*25%.*1 line$/),
    ])
  })

  it('folds the smaller categories into one', () => {
    const categories = Array.from({ length: 8 }, (_, index) =>
      category({
        category_id: `c${index}`,
        category_name: `Category ${index}`,
        amount: String(100 - index),
        line_count: 1,
      }),
    )

    const [breakdown] = breakdownByCurrency(categories, 6)

    expect(breakdown.bars.map((bar) => bar.label)).toEqual([
      'Category 0',
      'Category 1',
      'Category 2',
      'Category 3',
      'Category 4',
      'Category 5',
      'Other categories (2)',
    ])
    expect(breakdown.bars[6].amount).toBe(94 + 93)
    expect(breakdown.bars[6].lineCount).toBe(2)
  })

  it('keeps each currency apart', () => {
    setup({
      supplier: detail({
        categories: [
          category(),
          category({ currency: 'SEK', amount: '90.00' }),
        ],
      }),
    })

    expect(
      screen.getByRole('region', { name: 'Spend by category in DKK' }),
    ).toBeTruthy()
    expect(
      screen.getByRole('region', { name: 'Spend by category in SEK' }),
    ).toBeTruthy()
  })

  it('explains an empty breakdown', () => {
    setup({ supplier: detail({ categories: [] }) })

    expect(screen.getByText(/have lines yet/)).toBeTruthy()
  })
})

describe('SupplierDetailPanel — latest invoices', () => {
  function invoice(
    overrides: Partial<VendorInvoiceRead> = {},
  ): VendorInvoiceRead {
    return {
      id: 'i1',
      invoice_number: 'INV-2041',
      voucher_number: '4821',
      invoice_date: '2026-09-18',
      company_name: 'Acme A/S',
      currency: 'EUR',
      total: '134.00',
      status: 'verified',
      ...overrides,
    }
  }

  it('lists each invoice with its total and status', () => {
    setup()

    const row = screen.getByText('INV-2041').closest('tr')
    expect(row).not.toBeNull()
    const cells = within(row as HTMLElement)
    expect(cells.getByText('€134.00')).toBeTruthy()
    expect(cells.getByText('Verified')).toBeTruthy()
  })

  it('names the company only when the invoices went to several', () => {
    setup()
    expect(screen.queryByRole('columnheader', { name: 'Company' })).toBeNull()
    cleanup()

    setup({
      supplier: detail({
        recent_invoices: [
          invoice(),
          invoice({
            id: 'i2',
            invoice_number: 'INV-2040',
            company_name: 'Acme Sverige AB',
          }),
        ],
      }),
    })
    expect(screen.getByRole('columnheader', { name: 'Company' })).toBeTruthy()
    expect(screen.getByText('Acme Sverige AB')).toBeTruthy()
  })

  it('falls back to the voucher it was posted on, then to a dash', () => {
    setup({
      supplier: detail({
        recent_invoices: [
          invoice({ invoice_number: null }),
          invoice({ id: 'i2', invoice_number: null, voucher_number: null }),
        ],
      }),
    })

    const rows = screen.getAllByRole('row').slice(1)
    expect(rows[0].textContent).toContain('Voucher 4821')
    expect(within(rows[1]).getAllByText('—')).toHaveLength(1)
  })

  it('says when only the latest are shown', () => {
    setup()

    expect(screen.getByText('The latest 1 of 14')).toBeTruthy()
  })
})

describe('SupplierDetailPanel — navigation and states', () => {
  it('goes back to the suppliers and on to their spend lines', () => {
    const props = setup()

    fireEvent.click(screen.getByRole('button', { name: 'Back to suppliers' }))
    fireEvent.click(screen.getByRole('button', { name: /View spend lines/ }))

    expect(props.onBack).toHaveBeenCalled()
    expect(props.onViewLines).toHaveBeenCalled()
  })

  it('holds the page’s place while loading', () => {
    setup({ loading: true, supplier: undefined })

    expect(screen.getByTestId('supplier-loading')).toBeTruthy()
  })

  it('says when the supplier is not the organization’s', () => {
    setup({ notFound: true, error: true, supplier: undefined })

    expect(screen.getByText('Supplier not found')).toBeTruthy()
    expect(screen.queryByText('Couldn’t load this supplier')).toBeNull()
  })

  it('shows an error instead of an empty page', () => {
    setup({ error: true, supplier: undefined })

    expect(screen.getByText('Couldn’t load this supplier')).toBeTruthy()
  })
})
