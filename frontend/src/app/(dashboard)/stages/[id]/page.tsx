'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button, Card, LoadingOverlay, Modal } from '@/components/ui';
import { StageForm } from '@/components/stages';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import { Stage, ApiError } from '@/types';

export default function EditStagePage() {
  const params = useParams();
  const router = useRouter();
  const stageId = params.id as string;
  const { hasPermission } = usePermissions();

  const [stage, setStage] = useState<Stage | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const canUpdateStage = hasPermission('stages.update');
  const canDeleteStage = hasPermission('stages.delete');

  useEffect(() => {
    const fetchStage = async () => {
      setIsLoading(true);
      try {
        const stageData = await api.getStage(stageId);
        setStage(stageData);
      } catch (err) {
        const apiError = err as ApiError;
        console.error('Error fetching stage:', apiError);
        setError(apiError.detail || 'Failed to load stage');
      } finally {
        setIsLoading(false);
      }
    };

    fetchStage();
  }, [stageId]);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteStage(stageId);
      router.push('/stages');
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.detail || 'Failed to delete stage');
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  if (isLoading) {
    return <LoadingOverlay message="Loading stage..." />;
  }

  if (error || !stage) {
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
        <Card>
          <div className="text-center py-12">
            <p className="text-red-600 mb-4">{error || 'Stage not found'}</p>
            <Button variant="secondary" onClick={() => router.push('/stages')}>
              Back to Stages
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  if (!canUpdateStage) {
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
        <AccessDenied resource="update stages" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
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

        <CanAccess permission="stages.delete">
          <Button variant="danger" onClick={() => setShowDeleteModal(true)}>
            Delete Stage
          </Button>
        </CanAccess>
      </div>

      <StageForm stage={stage} />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Stage"
      >
        <p className="text-gray-600">
          Are you sure you want to delete the stage <strong>{stage.title}</strong>?
          This action cannot be undone.
        </p>
        <div className="flex justify-end gap-3 mt-6">
          <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDelete} isLoading={isDeleting}>
            Delete Stage
          </Button>
        </div>
      </Modal>
    </div>
  );
}