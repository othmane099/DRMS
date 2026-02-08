'use client';

import React from 'react';
import Link from 'next/link';
import { StageForm } from '@/components/stages';
import { usePermissions } from '@/hooks/usePermissions';
import { AccessDenied } from '@/components/auth/AccessDenied';

export default function NewStagePage() {
  const { hasPermission } = usePermissions();
  const canCreateStage = hasPermission('stages.create');

  if (!canCreateStage) {
    return (
      <div>
        <div className="mb-6">
          <Link
            href="/stages"
            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Back to Stages
          </Link>
        </div>
        <AccessDenied resource="create stages" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <Link
          href="/stages"
          className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Back to Stages
        </Link>
      </div>

      <StageForm />
    </div>
  );
}