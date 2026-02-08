import { Input, Select } from '@/components/ui';
import { Category, Stage } from '@/types';

interface DocumentFiltersProps {
  search: string;
  categoryId: string;
  stageId: string;
  createdDate: string;
  archive: string;
  categories: Category[];
  stages: Stage[];
  onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onCategoryChange: (value: string) => void;
  onStageChange: (value: string) => void;
  onCreatedDateChange: (value: string) => void;
  onArchiveChange: (value: string) => void;
}

export function DocumentFilters({
  search,
  categoryId,
  stageId,
  createdDate,
  archive,
  categories,
  stages,
  onSearchChange,
  onCategoryChange,
  onStageChange,
  onCreatedDateChange,
  onArchiveChange,
}: DocumentFiltersProps) {
  const categoryOptions = [
    { value: '', label: 'All Categories' },
    ...categories.map((category) => ({
      value: category.id,
      label: category.title,
    })),
  ];

  const stageOptions = [
    { value: '', label: 'All Stages' },
    ...stages.map((stage) => ({
      value: stage.id,
      label: stage.title,
    })),
  ];

  const archiveOptions = [
    { value: '', label: 'Active Only' },
    { value: 'true', label: 'Archived Only' },
  ];

  return (
    <div className="flex flex-wrap gap-4">
      <Input
        type="text"
        placeholder="Search documents..."
        value={search}
        onChange={onSearchChange}
        className="w-full sm:w-64"
      />
      <Select
        value={categoryId}
        onChange={(e) => onCategoryChange(e.target.value)}
        options={categoryOptions}
        className="w-full sm:w-48"
      />
      <Select
        value={stageId}
        onChange={(e) => onStageChange(e.target.value)}
        options={stageOptions}
        className="w-full sm:w-48"
      />
      <Input
        type="date"
        placeholder="Created Date"
        value={createdDate}
        onChange={(e) => onCreatedDateChange(e.target.value)}
        className="w-full sm:w-48"
      />
      <Select
        value={archive}
        onChange={(e) => onArchiveChange(e.target.value)}
        options={archiveOptions}
        className="w-full sm:w-48"
      />
    </div>
  );
}