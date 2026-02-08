'use client';

import React, { useMemo } from 'react';
import { Button, Checkbox } from '@/components/ui';
import { Permission } from '@/types';

interface PermissionChecklistProps {
  permissions: Permission[];
  selectedPermissions: string[]; // Array of permission codes like "users.list"
  onSelectionChange: (permissions: string[]) => void;
}

export function PermissionChecklist({
  permissions,
  selectedPermissions,
  onSelectionChange,
}: PermissionChecklistProps) {
  // Group permissions by the first part of the code (before the dot)
  const permissionsByModule = useMemo(() => {
    return permissions.reduce((acc, permission) => {
      const module = permission.code.split('.')[0] || 'general';
      if (!acc[module]) {
        acc[module] = [];
      }
      acc[module].push(permission);
      return acc;
    }, {} as Record<string, Permission[]>);
  }, [permissions]);

  const handleToggle = (permissionCode: string) => {
    if (selectedPermissions.includes(permissionCode)) {
      onSelectionChange(selectedPermissions.filter((code) => code !== permissionCode));
    } else {
      onSelectionChange([...selectedPermissions, permissionCode]);
    }
  };

  const handleSelectAllModule = (module: string) => {
    const modulePermissionCodes = permissionsByModule[module].map((p) => p.code);
    const allSelected = modulePermissionCodes.every((code) => selectedPermissions.includes(code));

    if (allSelected) {
      onSelectionChange(selectedPermissions.filter((code) => !modulePermissionCodes.includes(code)));
    } else {
      onSelectionChange([...new Set([...selectedPermissions, ...modulePermissionCodes])]);
    }
  };

  const handleSelectAll = () => {
    if (selectedPermissions.length === permissions.length) {
      onSelectionChange([]);
    } else {
      onSelectionChange(permissions.map((p) => p.code));
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <span className="text-sm text-gray-500">
          {selectedPermissions.length} of {permissions.length} permissions selected
        </span>
        <Button type="button" variant="ghost" size="sm" onClick={handleSelectAll}>
          {selectedPermissions.length === permissions.length ? 'Deselect All' : 'Select All'}
        </Button>
      </div>

      <div className="space-y-6">
        {Object.entries(permissionsByModule).map(([module, modulePermissions]) => {
          const modulePermissionCodes = modulePermissions.map((p) => p.code);
          const allModuleSelected = modulePermissionCodes.every((code) =>
            selectedPermissions.includes(code)
          );
          const someModuleSelected = modulePermissionCodes.some((code) =>
            selectedPermissions.includes(code)
          );

          return (
            <div key={module} className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={allModuleSelected}
                    ref={(el) => {
                      if (el) {
                        el.indeterminate = someModuleSelected && !allModuleSelected;
                      }
                    }}
                    onChange={() => handleSelectAllModule(module)}
                    className="h-4 w-4 rounded border-gray-300 text-black focus:ring-black"
                  />
                  <h4 className="font-medium text-sm uppercase text-gray-700">
                    {module}
                  </h4>
                </div>
                <span className="text-xs text-gray-400">
                  {modulePermissionCodes.filter((code) => selectedPermissions.includes(code)).length}/
                  {modulePermissions.length}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 ml-6">
                {modulePermissions.map((permission) => (
                  <div key={permission.id} className="flex items-start gap-2">
                    <Checkbox
                      checked={selectedPermissions.includes(permission.code)}
                      onChange={() => handleToggle(permission.code)}
                    />
                    <div>
                      <span className="text-sm">{permission.name}</span>
                      {permission.description && (
                        <p className="text-xs text-gray-400">{permission.description}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
