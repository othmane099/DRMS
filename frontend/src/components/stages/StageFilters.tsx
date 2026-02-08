import { Input } from '@/components/ui/Input';

interface StageFiltersProps {
  search: string;
  onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function StageFilters({
  search,
  onSearchChange,
}: StageFiltersProps) {
  return (
    <div className="flex flex-wrap gap-4 mb-6">
      <Input
        type="text"
        placeholder="Search stages..."
        value={search}
        onChange={onSearchChange}
        className="w-full sm:w-64"
      />
    </div>
  );
}