import { Input } from '@/components/ui/Input';

interface CategoryFiltersProps {
  search: string;
  onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function CategoryFilters({
  search,
  onSearchChange,
}: CategoryFiltersProps) {
  return (
    <div className="flex flex-wrap gap-4 mb-6">
      <Input
        type="text"
        placeholder="Search categories..."
        value={search}
        onChange={onSearchChange}
        className="w-full sm:w-64"
      />
    </div>
  );
}