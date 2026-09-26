import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import type { InvoiceLineRead, VoucherGroupRead } from '#/lib/api/types'
import { VoucherTable } from './voucher-table'

function line(): InvoiceLineRead {
  return {
    id: 'l1',
    invoice_id: 'inv1',
    company_id: 'c1',
    item_name: null,
    description: 'Figma Organization, 12 seats',
    quantity: '12.0000',
    unit: 'pcs',
    unit_price: '100.0000',
    amount: '1200.00',
    native_account_code: '6200',
    origin: 'document_ai',
    sequence: 0,
    currency: 'DKK',
    base_currency: 'DKK',
    base_amount: '1200.00',
    fx_rate: '1',
    fx_rate_date: '2026-07-02',
    status: 'ai_categorized',
    level_1: 'Indirect',
    level_2: 'Technology',
    level_3: 'Software Subscriptions',
    account_code: '6200',
    account_name: 'Software',
    confidence: '0.910',
    rationale: 'matched',
    spend_category_id: 'cat-software',
    level_4: null,
    category_stale: false,
    needs_review: false,
    verified_fields: [],
  }
}

function group(overrides: Partial<VoucherGroupRead> = {}): VoucherGroupRead {
  return {
    voucher_id: 'V-1042',
    voucher_number: '1042',
    company_id: 'c1',
    accounting_date: '2026-07-02',
    entry_types: ['purchase_invoice'],
    entry_count: 1,
    amount: '1200.00',
    debit_total: '1200.00',
    credit_total: '1200.00',
    currency: 'DKK',
    unconverted_count: 0,
    vendor_id: 'v1',
    vendor_name: 'Contoso ApS',
    entries: [],
    lines: [line()],
    doc_status: 'processed',
    doc_error: null,
    invoice_number: 'INV-1',
    document_invoice_number: 'INV-1',
    totals_agree: true,
    document_total: '1500.00',
    invoice_total: '1500.00',
    invoice_currency: 'DKK',
    ...overrides,
  }
}

const MISMATCH = {
  totals_agree: false,
  document_total: '1625.00',
  invoice_total: '1500.00',
} as const

function renderTable(groups: Array<VoucherGroupRead>) {
  render(<VoucherTable groups={groups} onSelectEntry={vi.fn()} />)
}

afterEach(() => {
  cleanup()
})

describe('VoucherTable — document total against the ERP', () => {
  it('flags a voucher whose document states a different total', () => {
    renderTable([group(MISMATCH)])

    const marker = screen.getByLabelText(/document total differs/i)
    const label = marker.getAttribute('aria-label') ?? ''
    expect(label).toMatch(/DKK\s1,625\.00/)
    expect(label).toMatch(/DKK\s1,500\.00/)
    expect(marker.getAttribute('tabindex')).toBe('0')
  })

  it('says nothing when the totals agree', () => {
    renderTable([group()])

    expect(screen.queryByLabelText(/document total differs/i)).toBeNull()
  })

  it('says nothing when the document has not been read', () => {
    renderTable([group({ totals_agree: null, document_total: null })])

    expect(screen.queryByLabelText(/document total differs/i)).toBeNull()
  })

  it('warns above the lines when the voucher is expanded', () => {
    renderTable([group(MISMATCH)])

    fireEvent.click(screen.getByRole('button', { name: /Expand voucher 1042/ }))

    const note = screen.getByRole('note')
    expect(note.textContent).toMatch(/DKK\s1,625\.00/)
    expect(note.textContent).toMatch(/DKK\s1,500\.00/)
  })

  it('adds no warning above the lines of an agreeing voucher', () => {
    renderTable([group()])

    fireEvent.click(screen.getByRole('button', { name: /Expand voucher 1042/ }))

    expect(screen.queryByRole('note')).toBeNull()
  })
})
