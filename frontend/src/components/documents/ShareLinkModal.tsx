'use client';

import React, { useState, useEffect } from 'react';
import { Modal, Button, Input } from '@/components/ui';
import { api } from '@/lib/api';
import { Document, ApiError, ShareLinkInput, ShareLinkResponse } from '@/types';

interface ShareLinkModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: Document | null;
  onSuccess: (url: string) => void;
  generateLinkFn?: (documentId: string, data: ShareLinkInput) => Promise<ShareLinkResponse>;
}

export function ShareLinkModal({ isOpen, onClose, document, onSuccess, generateLinkFn }: ShareLinkModalProps) {
  const [formData, setFormData] = useState({
    expiration_date: '',
    password: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);

  // Reset form when modal opens/closes or document changes
  useEffect(() => {
    if (isOpen) {
      setFormData({
        expiration_date: '',
        password: '',
      });
      setErrors({});
      setApiError(null);
      setGeneratedUrl(null);
    }
  }, [isOpen, document]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    // Only validate expiration date if it's provided
    if (formData.expiration_date) {
      // Validate that expiration date is in the future
      const selectedDate = new Date(formData.expiration_date);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (selectedDate < today) {
        newErrors.expiration_date = 'Expiration date must be in the future';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm() || !document) {
      return;
    }

    setIsLoading(true);
    setApiError(null);

    try {
      const requestData: ShareLinkInput = {};

      // Only include expiration_date if it's provided
      if (formData.expiration_date) {
        requestData.expiration_date = formData.expiration_date;
      }

      // Only include password if it's provided
      if (formData.password) {
        requestData.password = formData.password;
      }

      const response = await (generateLinkFn ?? api.generateShareLink.bind(api))(document.id, requestData);

      // Construct the full URL using the token from the backend
      const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
      const fullUrl = `${baseUrl}/share/${response.token}`;

      setGeneratedUrl(fullUrl);
      onSuccess(fullUrl);
    } catch (error) {
      const apiError = error as ApiError;
      setApiError(apiError.detail || 'Failed to generate share link');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyUrl = () => {
    if (generatedUrl) {
      navigator.clipboard.writeText(generatedUrl);
      // You could add a toast notification here
    }
  };

  const handleClose = () => {
    setGeneratedUrl(null);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={generatedUrl ? 'Share Link Generated' : 'Generate Share Link'}
    >
      {!generatedUrl ? (
        <form onSubmit={handleSubmit}>
          {apiError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">
              {apiError}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <p className="text-sm text-gray-600 mb-4">
                Generate a secure, encrypted link to share <strong>{document?.name}</strong> with external users.
              </p>
            </div>

            <Input
              label="Expiration Date (Optional)"
              type="date"
              value={formData.expiration_date}
              onChange={(e) =>
                setFormData({ ...formData, expiration_date: e.target.value })
              }
              error={errors.expiration_date}
              min={new Date().toISOString().split('T')[0]}
              placeholder="No expiration"
            />

            <Input
              label="Password (Optional)"
              type="password"
              value={formData.password}
              onChange={(e) =>
                setFormData({ ...formData, password: e.target.value })
              }
              error={errors.password}
              placeholder="Leave empty for no password protection"
            />
          </div>

          <div className="flex justify-end gap-3 mt-6">
            <Button variant="secondary" onClick={handleClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isLoading}>
              Generate Link
            </Button>
          </div>
        </form>
      ) : (
        <div>
          <div className="mb-4">
            <div className="flex items-center justify-center mb-4">
              <div className="flex-shrink-0 w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-green-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
            </div>
            <p className="text-center text-gray-700 mb-4">
              Your share link has been generated successfully!
            </p>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Share Link
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={generatedUrl}
                readOnly
                className="flex-1 px-3 py-2 border border-gray-300 rounded bg-gray-50 text-sm font-mono"
              />
              <Button variant="secondary" onClick={handleCopyUrl}>
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
                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                  />
                </svg>
              </Button>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4">
            <div className="flex items-start gap-2">
              <svg
                className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div className="text-sm text-blue-700">
                <p className="font-medium mb-1">Important Information:</p>
                <ul className="list-disc list-inside space-y-1">
                  {formData.expiration_date ? (
                    <li>This link will expire on {new Date(formData.expiration_date).toLocaleDateString()}</li>
                  ) : (
                    <li>This link has no expiration date</li>
                  )}
                  {formData.password && <li>Password protection is enabled</li>}
                  <li>The link is encrypted and secure</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <Button onClick={handleClose}>
              Close
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}