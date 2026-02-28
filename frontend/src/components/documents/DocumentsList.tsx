'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button, Card, Pagination, LoadingOverlay, Modal, Toast } from '@/components/ui';
import { DocumentTable, DocumentFilters, DocumentModal, ShareLinkModal, DocumentChatModal } from '@/components/documents';
import { CanAccess } from '@/components/auth/CanAccess';
import { AccessDenied } from '@/components/auth/AccessDenied';
import { usePermissions } from '@/hooks/usePermissions';
import { api } from '@/lib/api';
import {
  Document,
  DocumentVersion,
  PaginatedResponse,
  DocumentFilters as DocumentFiltersType,
  ApiError,
  Category,
  Stage,
  ShareLinkResponse,
} from '@/types';
import { debounce } from '@/lib/utils';

interface DocumentsListProps {
  title: string;
  description: string;
  basePath: string;
  permissions: {
    list: string;
    listMy?: string;
    create: string;
    edit: string;
    delete: string;
    share: string;
    archive: string;
    chat?: string;
  };
  apiFunctions: {
    getDocuments: (filters: DocumentFiltersType) => Promise<PaginatedResponse<Document>>;
    deleteDocument: (id: string) => Promise<void>;
    archiveDocument: (id: string) => Promise<Document>;
    updateDocument: (id: string, data: any) => Promise<Document>;
    generateShareLink: (id: string, data: any) => Promise<ShareLinkResponse>;
    chatWithVersion?: (docId: string, versionId: string, msg: string) => Promise<{ message: string }>;
    getVersions?: (id: string) => Promise<DocumentVersion[]>;
  };
}

export function DocumentsList({ title, description, basePath, permissions, apiFunctions }: DocumentsListProps) {
  const { hasPermission, hasAnyPermission, isSuperuser } = usePermissions();
  const [documents, setDocuments] = useState<PaginatedResponse<Document> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [accessDenied, setAccessDenied] = useState(false);

  // Dropdown data
  const [categories, setCategories] = useState<Category[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);

  // Modal states
  const [showDocumentModal, setShowDocumentModal] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<Document | undefined>(undefined);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showShareLinkModal, setShowShareLinkModal] = useState(false);
  const [documentToShare, setDocumentToShare] = useState<Document | null>(null);

  // Chat state
  const [showChatModal, setShowChatModal] = useState(false);
  const [chatDocument, setChatDocument] = useState<Document | null>(null);
  const [chatVersionId, setChatVersionId] = useState<string | null>(null);
  const [isFetchingChatVersion, setIsFetchingChatVersion] = useState(false);

  // Toast notification state
  const [toast, setToast] = useState<{
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    isVisible: boolean;
  }>({
    message: '',
    type: 'success',
    isVisible: false,
  });

  // Filters
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [stageId, setStageId] = useState('');
  const [createdDate, setCreatedDate] = useState('');
  const [archive, setArchive] = useState('');
  const [onlyMy, setOnlyMy] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // Permission checks
  const listPermissions = [permissions.list, ...(permissions.listMy ? [permissions.listMy] : [])];
  const canViewDocuments = hasAnyPermission(listPermissions);
  // Show "my documents only" toggle when user can list all docs (has full list perm or is superuser)
  const canViewAll = hasPermission(permissions.list) || isSuperuser();

  // Fetch dropdown data on mount
  useEffect(() => {
    fetchDropdownData();
  }, []);

  const fetchDropdownData = async () => {
    try {
      const [categoriesData, stagesData] = await Promise.all([
        api.getCategories({ page_size: 1000 }),
        api.getStages({ page_size: 1000 }),
      ]);

      setCategories(categoriesData.data);
      setStages(stagesData.data);
    } catch (err) {
      console.error('Failed to fetch dropdown data:', err);
    }
  };

  const fetchDocuments = useCallback(async () => {
    // Check permission before fetching
    if (!canViewDocuments) {
      setAccessDenied(true);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const filters: DocumentFiltersType = {
        page,
        page_size: pageSize,
      };
      if (search) filters.search = search;
      if (categoryId) filters.category_id = categoryId;
      if (stageId) filters.stage_id = stageId;
      if (createdDate) filters.created_date = createdDate;
      if (archive !== '') filters.archive = archive === 'true';
      if (onlyMy) filters.only_my = true;

      const data = await apiFunctions.getDocuments(filters);
      setDocuments(data);
    } catch (error) {
      const apiError = error as ApiError;
      // Handle 403 errors gracefully
      if (apiError.status === 403) {
        setAccessDenied(true);
      } else {
        console.error('Failed to fetch documents:', error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [page, search, categoryId, stageId, createdDate, archive, onlyMy, canViewDocuments]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Debounced search
  const debouncedSearch = useCallback(
    debounce((value: string) => {
      setSearch(value);
      setPage(1);
    }, 300),
    []
  );

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearchInput(value);
    debouncedSearch(value);
  };

  const handleCategoryChange = (value: string) => {
    setCategoryId(value);
    setPage(1);
  };

  const handleStageChange = (value: string) => {
    setStageId(value);
    setPage(1);
  };

  const handleCreatedDateChange = (value: string) => {
    setCreatedDate(value);
    setPage(1);
  };

  const handleArchiveChange = (value: string) => {
    setArchive(value);
    setPage(1);
  };

  const handleOnlyMyChange = (value: boolean) => {
    setOnlyMy(value);
    setPage(1);
  };

  const handleCreateDocument = () => {
    setSelectedDocument(undefined);
    setShowDocumentModal(true);
  };

  const handleEditDocument = (document: Document) => {
    setSelectedDocument(document);
    setShowDocumentModal(true);
  };

  const handleDeleteDocument = (document: Document) => {
    setDocumentToDelete(document);
    setShowDeleteModal(true);
  };

  const handleArchiveDocument = async (document: Document) => {
    try {
      await apiFunctions.archiveDocument(document.id);
      const message = document.archive ? 'Document unarchived successfully' : 'Document archived successfully';
      showToast(message, 'success');
      fetchDocuments();
    } catch (error) {
      const apiError = error as ApiError;
      console.error('Failed to toggle archive status:', error);
      showToast(apiError.detail || 'Failed to update document', 'error');
    }
  };

  const handleShareDocument = (document: Document) => {
    setDocumentToShare(document);
    setShowShareLinkModal(true);
  };

  const handleShareLinkSuccess = (token: string) => {
    showToast('Share link generated successfully', 'success');
  };

  const handleChatClick = async (document: Document) => {
    if (!apiFunctions.chatWithVersion) return;
    setChatDocument(document);
    setIsFetchingChatVersion(true);
    try {
      const getVersions = apiFunctions.getVersions ?? ((id: string) => api.getDocumentVersions(id));
      const versions = await getVersions(document.id);
      const current = versions.find((v) => v.is_current) ?? versions[0];
      if (!current) {
        showToast('No version found for this document', 'error');
        return;
      }
      setChatVersionId(current.id);
      setShowChatModal(true);
    } catch {
      showToast('Failed to load document version', 'error');
    } finally {
      setIsFetchingChatVersion(false);
    }
  };

  const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
    setToast({ message, type, isVisible: true });
  };

  const hideToast = () => {
    setToast((prev) => ({ ...prev, isVisible: false }));
  };

  const confirmDelete = async () => {
    if (!documentToDelete) return;

    setIsDeleting(true);
    try {
      await apiFunctions.deleteDocument(documentToDelete.id);
      setShowDeleteModal(false);
      setDocumentToDelete(null);
      showToast('Document deleted successfully', 'success');
      fetchDocuments();
    } catch (error) {
      const apiError = error as ApiError;
      console.error('Failed to delete document:', error);
      showToast(apiError.detail || 'Failed to delete document', 'error');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDocumentSuccess = () => {
    const message = selectedDocument ? 'Document updated successfully' : 'Document created successfully';
    showToast(message, 'success');
    fetchDocuments();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{title}</h1>
          <p className="text-gray-500">{description}</p>
        </div>
        <CanAccess permission={permissions.create}>
          <Button onClick={handleCreateDocument}>
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
                d="M12 4v16m8-8H4"
              />
            </svg>
            Add Document
          </Button>
        </CanAccess>
      </div>

      <Card padding="none">
        {accessDenied ? (
          <AccessDenied resource="documents" />
        ) : (
          <>
            <div className="p-4 border-b border-gray-200">
              <DocumentFilters
                search={searchInput}
                categoryId={categoryId}
                stageId={stageId}
                createdDate={createdDate}
                archive={archive}
                categories={categories}
                stages={stages}
                onSearchChange={handleSearchChange}
                onCategoryChange={handleCategoryChange}
                onStageChange={handleStageChange}
                onCreatedDateChange={handleCreatedDateChange}
                onArchiveChange={handleArchiveChange}
                showOnlyMyFilter={canViewAll}
                onlyMy={onlyMy}
                onOnlyMyChange={handleOnlyMyChange}
              />
            </div>

            {isLoading ? (
              <LoadingOverlay message="Loading documents..." />
            ) : documents && documents.data ? (
              <>
                <DocumentTable
                  documents={documents.data}
                  onEdit={handleEditDocument}
                  onDelete={handleDeleteDocument}
                  onArchive={handleArchiveDocument}
                  onShare={handleShareDocument}
                  onChat={apiFunctions.chatWithVersion ? handleChatClick : undefined}
                  editPermission={permissions.edit}
                  deletePermission={permissions.delete}
                  sharePermission={permissions.share}
                  archivePermission={permissions.archive}
                  chatPermission={permissions.chat}
                  basePath={basePath}
                />
                <Pagination
                  currentPage={documents.page}
                  totalPages={documents.total_pages || Math.ceil(documents.total / pageSize)}
                  onPageChange={setPage}
                />
              </>
            ) : (
              <div className="py-12 text-center text-gray-500">
                Failed to load documents
              </div>
            )}
          </>
        )}
      </Card>

      {/* Create/Edit Document Modal */}
      <DocumentModal
        isOpen={showDocumentModal}
        onClose={() => setShowDocumentModal(false)}
        document={selectedDocument}
        onSuccess={handleDocumentSuccess}
        updateFn={apiFunctions.updateDocument}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        title="Delete Document"
      >
        {documentToDelete && (
          <>
            <div className="flex items-start gap-3 mb-4">
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                <svg
                  className="w-5 h-5 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Are you sure you want to delete this document?
                </h3>
                <p className="text-gray-600">
                  You are about to delete the document <strong className="text-gray-900">{documentToDelete.name}</strong>.
                  This action cannot be undone.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button
                variant="secondary"
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button variant="danger" onClick={confirmDelete} isLoading={isDeleting}>
                Delete Document
              </Button>
            </div>
          </>
        )}
      </Modal>

      {/* Share Link Modal */}
      <ShareLinkModal
        isOpen={showShareLinkModal}
        onClose={() => setShowShareLinkModal(false)}
        document={documentToShare}
        onSuccess={handleShareLinkSuccess}
        generateLinkFn={apiFunctions.generateShareLink}
      />

      {/* Chat Modal */}
      {chatDocument && chatVersionId && apiFunctions.chatWithVersion && (
        <DocumentChatModal
          isOpen={showChatModal}
          onClose={() => {
            setShowChatModal(false);
            setChatDocument(null);
            setChatVersionId(null);
          }}
          documentName={chatDocument.name}
          onSend={(msg) => apiFunctions.chatWithVersion!(chatDocument.id, chatVersionId, msg)}
        />
      )}

      {/* Toast Notification */}
      <Toast
        message={toast.message}
        type={toast.type}
        isVisible={toast.isVisible}
        onClose={hideToast}
      />
    </div>
  );
}