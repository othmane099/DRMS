'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { Button, Input, LoadingOverlay } from '@/components/ui';
import { api } from '@/lib/api';
import { ApiError } from '@/types';

export default function SharedDocumentPage() {
  const params = useParams();
  const token = params.token as string;

  const [password, setPassword] = useState('');
  const [isPasswordRequired, setIsPasswordRequired] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [documentUrl, setDocumentUrl] = useState<string | null>(null);
  const [contentType, setContentType] = useState<string>('');

  useEffect(() => {
    loadDocument();
  }, [token]);

  const loadDocument = async (submittedPassword?: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const blob = await api.previewSharedDocument(token, submittedPassword);
      const url = URL.createObjectURL(blob);
      setDocumentUrl(url);
      setContentType(blob.type);
      setIsPasswordRequired(false);
    } catch (err) {
      const apiError = err as ApiError;

      if (apiError.status === 401) {
        setIsPasswordRequired(true);
        if (submittedPassword) {
          setError('Invalid password or link has expired');
        } else {
          setError('Password is required to view this document');
        }
      } else if (apiError.status === 403) {
        setError('Invalid password or link has expired');
      } else if (apiError.status === 404) {
        setError('Document not found or link has expired');
      } else {
        setError(apiError.detail || 'Failed to load document');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadDocument(password);
  };

  const renderDocumentViewer = () => {
    if (!documentUrl) return null;

    // Handle PDF files
    if (contentType === 'application/pdf') {
      return (
        <iframe
          src={documentUrl}
          className="w-full h-screen border-0"
          title="Document Preview"
        />
      );
    }

    // Handle images
    if (contentType.startsWith('image/')) {
      return (
        <div className="flex items-center justify-center min-h-screen bg-gray-100 p-4">
          <img
            src={documentUrl}
            alt="Document Preview"
            className="max-w-full max-h-screen object-contain"
          />
        </div>
      );
    }

    // Handle text files
    if (contentType.startsWith('text/')) {
      return (
        <iframe
          src={documentUrl}
          className="w-full h-screen border-0 bg-white p-4"
          title="Document Preview"
        />
      );
    }

    // For other file types, show a download option
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100">
        <div className="bg-white p-8 rounded-lg shadow-md text-center max-w-md">
          <svg
            className="w-16 h-16 mx-auto mb-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
            />
          </svg>
          <h2 className="text-xl font-semibold mb-2">Document Ready</h2>
          <p className="text-gray-600 mb-4">
            This file type cannot be previewed in the browser.
          </p>
          <a
            href={documentUrl}
            download
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Download Document
          </a>
        </div>
      </div>
    );
  };

  if (isLoading && !isPasswordRequired) {
    return <LoadingOverlay message="Loading document..." />;
  }

  if (isPasswordRequired) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
        <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
          <div className="flex items-center justify-center mb-6">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center">
              <svg
                className="w-6 h-6 text-blue-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
            </div>
          </div>

          <h1 className="text-2xl font-bold text-center mb-2">Password Required</h1>
          <p className="text-gray-600 text-center mb-6">
            This document is password-protected. Please enter the password to view it.
          </p>

          <form onSubmit={handlePasswordSubmit}>
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">
                {error}
              </div>
            )}

            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
              autoFocus
            />

            <Button type="submit" className="w-full mt-4" isLoading={isLoading}>
              View Document
            </Button>
          </form>
        </div>
      </div>
    );
  }

  if (error && !isPasswordRequired) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
        <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md text-center">
          <div className="flex items-center justify-center mb-4">
            <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
              <svg
                className="w-6 h-6 text-red-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
          </div>

          <h1 className="text-2xl font-bold mb-2">Unable to Load Document</h1>
          <p className="text-gray-600 mb-4">{error}</p>

          <p className="text-sm text-gray-500">
            Please contact the person who shared this link with you.
          </p>
        </div>
      </div>
    );
  }

  return renderDocumentViewer();
}