import { afterEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import type { SpendCoverageRow } from '#/lib/api/types'
import { SpendCoverage } from './spend-coverage'

function row(overrides: Partial<SpendCoverageRow> = {}): SpendCoverageRow {
  return {
    currency: 'DKK',
    voucher_count: 37,
    unconverted_vouchers: 0,
    posted_spend: '12000.00',
    categorized_spend: '9000.00',
    line_count: 57,
    categorized_lines: 45,
    verified_lines: 10,
    needs_review_lines: 5,
    uncategorized_lines: 10,
    failed_lines: 2,
    ...overrides,
  }
}

function metric(name: string): HTMLElement {
  return screen.getByRole('region', { name })
}

afterEach(() => {
  cleanup()
})

describe('SpendCoverage', () => {
  it('states the posted spend and how many vouchers it covers', () => {
    render(<SpendCoverage rows={[row()]} />)

    const posted = metric('Posted spend')
    expect(posted.textContent).toMatch(/DKK\s12,000\.00/)
    expect(posted.textContent).toContain('37 vouchers')
  })

  it('states the categorized spend as a share of the posted spend', () => {
    render(<SpendCoverage rows={[row()]} />)

    const categorized = metric('Categorized spend')
    expect(categorized.textContent).toMatch(/DKK\s9,000\.00/)
    expect(categorized.textContent).toContain('75% of posted spend')
    expect(
      within(categorized)
        .getByRole('progressbar')
        .getAttribute('aria-valuenow'),
    ).toBe('75')
  })

  it('counts the categorized lines and splits them by state', () => {
    render(<SpendCoverage rows={[row()]} />)

    const lines = metric('Lines categorized')
    expect(lines.textContent).toContain('45 of 57')
    const bar = within(lines).getByRole('img')
    const label = bar.getAttribute('aria-label') ?? ''
    expect(label).toContain('Verified 10')
    expect(label).toContain('AI categorized 30')
    expect(label).toContain('Needs review 5')
    expect(label).toContain('Uncategorized 10')
    expect(label).toContain('Failed 2')
  })

  it('leaves an empty state out of the legend', () => {
    render(<SpendCoverage rows={[row({ failed_lines: 0 })]} />)

    expect(within(metric('Lines categorized')).queryByText('Failed')).toBeNull()
  })

  it('says how many vouchers could not be converted', () => {
    render(<SpendCoverage rows={[row({ unconverted_vouchers: 3 })]} />)

    expect(metric('Posted spend').textContent).toContain('3 not converted')
  })

  it('does not invent a share when nothing was posted', () => {
    render(<SpendCoverage rows={[row({ posted_spend: '0' })]} />)

    const categorized = metric('Categorized spend')
    expect(categorized.textContent).toContain('No posted spend to compare with')
    expect(within(categorized).queryByRole('progressbar')).toBeNull()
  })

  it('names the currency on each card when there are several', () => {
    render(<SpendCoverage rows={[row(), row({ currency: 'EUR' })]} />)

    expect(metric('Posted spend · DKK')).toBeTruthy()
    expect(metric('Posted spend · EUR')).toBeTruthy()
  })

  it('holds its place while loading', () => {
    render(<SpendCoverage rows={undefined} />)

    expect(screen.getByTestId('spend-coverage-loading')).toBeTruthy()
  })

  it('shows nothing when no vouchers are listed', () => {
    const { container } = render(
      <SpendCoverage rows={[row({ voucher_count: 0 })]} />,
    )

    expect(container.textContent).toBe('')
  })
})
