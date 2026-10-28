import { Button } from '@/shared/ui/Button'

interface PaginationProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  summary: string
  prevLabel: string
  nextLabel: string
}

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
  summary,
  prevLabel,
  nextLabel,
}: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-[var(--color-muted)]">
      <p>{summary}</p>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          {prevLabel}
        </Button>
        <span className="text-[var(--color-text)]">
          {page} / {totalPages}
        </span>
        <Button
          variant="secondary"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
        >
          {nextLabel}
        </Button>
      </div>
    </div>
  )
}
