import { useTranslation } from 'react-i18next'

import type { TaskAssignee } from '@/features/work/types'
import { PersonPicker } from '@/shared/ui/PersonPicker'

interface FollowersPickerProps {
  users: TaskAssignee[]
  selectedIds: string[]
  excludeIds?: string[]
  disabled?: boolean
  onToggle: (userId: string, checked: boolean) => void
}

/** Work-context wrapper around the shared multi PersonPicker. */
export function FollowersPicker({
  users,
  selectedIds,
  excludeIds = [],
  disabled = false,
  onToggle,
}: FollowersPickerProps) {
  const { t } = useTranslation()

  return (
    <PersonPicker
      mode="multiple"
      people={users}
      value={selectedIds}
      excludeIds={excludeIds}
      disabled={disabled}
      label={t('work.create.fieldFollowers')}
      hint={t('work.create.followersHint')}
      emptyLabel={t('work.create.noFollowers')}
      searchPlaceholder={t('work.create.searchFollowersPlaceholder')}
      recentStorageKey="karam.work.recentFollowers"
      onToggle={onToggle}
    />
  )
}
