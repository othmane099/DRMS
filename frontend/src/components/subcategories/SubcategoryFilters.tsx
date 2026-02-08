import { Input, Select } from '@/components/ui';
import { Category } from '@/types';

interface SubcategoryFiltersProps {
  search: string;
  categoryId: string;
  categories: Category[];
  onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onCategoryChange: (value: string) => void;
}

export function SubcategoryFilters({
  search,
  categoryId,
  categories,
  onSearchChange,
  onCategoryChange,
}: SubcategoryFiltersProps) {
  const categoryOptions = [
    { value: '', label: 'All Categories' },
    ...categories.map((category) => ({
      value: category.id,
      label: category.title,
    })),
  ];

  return (
    <div className="flex flex-wrap gap-4 mb-6">
      <Input
        type="text"
        placeholder="Search subcategories..."
        value={search}
        onChange={onSearchChange}
        className="w-full sm:w-64"
      />
      <Select
        value={categoryId}
        onChange={(e) => onCategoryChange(e.target.value)}
        options={categoryOptions}
        className="w-full sm:w-64"
      />
    </div>
  );
}