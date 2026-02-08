import { Input } from '@/components/ui/Input';

interface TagFiltersProps {
  search: string;
  onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function TagFilters({
  search,
  onSearchChange,
}: TagFiltersProps) {
  return (
    <div className="flex flex-wrap gap-4 mb-6">
      <Input
        type="text"
        placeholder="Search tags..."
        value={search}
        onChange={onSearchChange}
        className="w-full sm:w-64"
      />
    </div>
  );
}
