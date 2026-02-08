'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button, Modal, Select } from '@/components/ui';
import { api } from '@/lib/api';
import { Role, BulkAction, ApiError } from '@/types';

interface BulkActionsDropdownProps {
  selectedIds: string[];
  roles: Role[];
  onActionComplete: () => void;
}

export function BulkActionsDropdown({
  selectedIds,
  roles,
  onActionComplete,
}: BulkActionsDropdownProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);
  const [pendingAction, setPendingAction] = useState<BulkAction['action'] | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleAction = (action: BulkAction['action']) => {
    setPendingAction(action);
    setShowDropdown(false);

    if (action === 'assign_role') {
      setShowRoleModal(true);
    } else {
      setShowConfirmModal(true);
    }
  };

  const executeAction = async () => {
    if (!pendingAction) return;

    setIsLoading(true);
    setError(null);

    try {
      const bulkAction: BulkAction = {
        user_ids: selectedIds,
        action: pendingAction,
      };

      if (pendingAction === 'assign_role' && selectedRoleId) {
        bulkAction.parameters = { role_id: selectedRoleId };
      }

      await api.bulkUserAction(bulkAction);
      setShowConfirmModal(false);
      setShowRoleModal(false);
      setPendingAction(null);
      setSelectedRoleId('');
      onActionComplete();
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || 'Failed to perform action');
    } finally {
      setIsLoading(false);
    }
  };

  const getActionLabel = () => {
    switch (pendingAction) {
      case 'activate':
        return 'Activate';
      case 'deactivate':
        return 'Deactivate';
      case 'delete':
        return 'Delete';
      case 'assign_role':
        return 'Assign Role';
      default:
        return '';
    }
  };

  if (selectedIds.length === 0) return null;

  return (
    <>
      <div className="relative" ref={dropdownRef}>
        <Button variant="secondary" onClick={() => setShowDropdown(!showDropdown)}>
          Bulk Actions ({selectedIds.length})
          <svg
            className="w-4 h-4 ml-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </Button>

        {showDropdown && (
          <div className="absolute left-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-gray-200 py-1 z-50">
            <button
              onClick={() => handleAction('activate')}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Activate Users
            </button>
            <button
              onClick={() => handleAction('deactivate')}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Deactivate Users
            </button>
            <button
              onClick={() => handleAction('assign_role')}
              className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              Assign Role
            </button>
            <hr className="my-1" />
            <button
              onClick={() => handleAction('delete')}
              className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50"
            >
              Delete Users
            </button>
          </div>
        )}
      </div>

      {/* Confirm Modal */}
      <Modal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title={`${getActionLabel()} ${selectedIds.length} Users`}
      >
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mb-4">
            {error}
          </div>
        )}
        <p className="text-sm text-gray-600">
          Are you sure you want to {pendingAction} {selectedIds.length} user(s)?
          {pendingAction === 'delete' && (
            <span className="text-red-600 block mt-2">
              This action cannot be undone.
            </span>
          )}
        </p>
        <div className="flex justify-end gap-3 mt-6">
          <Button
            variant="secondary"
            onClick={() => setShowConfirmModal(false)}
          >
            Cancel
          </Button>
          <Button
            variant={pendingAction === 'delete' ? 'danger' : 'primary'}
            onClick={executeAction}
            isLoading={isLoading}
          >
            {getActionLabel()}
          </Button>
        </div>
      </Modal>

      {/* Role Assignment Modal */}
      <Modal
        isOpen={showRoleModal}
        onClose={() => setShowRoleModal(false)}
        title={`Assign Role to ${selectedIds.length} Users`}
      >
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm mb-4">
            {error}
          </div>
        )}
        <Select
          label="Select Role"
          value={selectedRoleId}
          onChange={(e) => setSelectedRoleId(e.target.value)}
          options={[
            { value: '', label: 'No Role' },
            ...roles.map((role) => ({ value: role.id, label: role.name })),
          ]}
        />
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setShowRoleModal(false)}>
            Cancel
          </Button>
          <Button onClick={executeAction} isLoading={isLoading}>
            Assign Role
          </Button>
        </div>
      </Modal>
    </>
  );
}
