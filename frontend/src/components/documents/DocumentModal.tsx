'use client';

import React, { useState, useEffect } from 'react';
import { Modal, Button, Input, Select } from '@/components/ui';
import { api } from '@/lib/api';
import {
  Document,
  DocumentCreateInput,
  DocumentUpdateInput,
  ApiError,
  Category,
  Subcategory,
  Stage,
  UserBasicId,
  Tag,
} from '@/types';

interface DocumentModalProps {
  isOpen: boolean;
  onClose: () => void;
  document?: Document;
  onSuccess: () => void;
  updateFn?: (id: string, data: DocumentUpdateInput) => Promise<Document>;
}

export function DocumentModal({ isOpen, onClose, document, onSuccess, updateFn }: DocumentModalProps) {
  const isEditing = !!document;

  const [formData, setFormData] = useState({
    name: document?.name || '',
    category_id: document?.category_id || '',
    subcategory_id: document?.subcategory_id || '',
    stage_id: document?.stage_id || '',
    assigned_to: document?.assigned_to || '',
    description: document?.description || '',
    tag_ids: document?.tags?.map((tag) => tag.id) || [] as string[],
  });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [categories, setCategories] = useState<Category[]>([]);
  const [subcategories, setSubcategories] = useState<Subcategory[]>([]);
  const [stages, setStages] = useState<Stage[]>([]);
  const [users, setUsers] = useState<UserBasicId[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Fetch dropdown data
  useEffect(() => {
    if (isOpen) {
      fetchDropdownData();
    }
  }, [isOpen]);

  // Reset form when modal opens/closes or document changes
  useEffect(() => {
    if (isOpen) {
      setFormData({
        name: document?.name || '',
        category_id: document?.category_id || '',
        subcategory_id: document?.subcategory_id || '',
        stage_id: document?.stage_id || '',
        assigned_to: document?.assigned_to || '',
        description: document?.description || '',
        tag_ids: document?.tags?.map((tag) => tag.id) || [],
      });
      setSelectedFile(null);
      setErrors({});
      setApiError(null);
    }
  }, [isOpen, document]);

  // Fetch subcategories when category changes
  useEffect(() => {
    if (formData.category_id) {
      fetchSubcategories(formData.category_id);
    } else {
      setSubcategories([]);
      setFormData((prev) => ({ ...prev, subcategory_id: '' }));
    }
  }, [formData.category_id]);

  const fetchDropdownData = async () => {
    setIsLoadingData(true);
    try {
      const [categoriesData, stagesData, usersData, tagsData] = await Promise.all([
        api.getCategories({ page_size: 1000 }),
        api.getStages({ page_size: 1000 }),
        api.getUsersForAssignment(),
        api.getTags({ page_size: 1000 }),
      ]);

      setCategories(categoriesData.data);
      setStages(stagesData.data);
      setUsers(usersData);
      setTags(tagsData.data);

      // If editing and has category, fetch subcategories
      if (document?.category_id) {
        const subcategoriesData = await api.getSubcategories({
          category_id: document.category_id,
          page_size: 1000,
        });
        setSubcategories(subcategoriesData.data);
      }
    } catch (err) {
      console.error('Failed to fetch dropdown data:', err);
    } finally {
      setIsLoadingData(false);
    }
  };

  const fetchSubcategories = async (categoryId: string) => {
    try {
      const data = await api.getSubcategories({
        category_id: categoryId,
        page_size: 1000,
      });
      setSubcategories(data.data);
    } catch (err) {
      console.error('Failed to fetch subcategories:', err);
      setSubcategories([]);
    }
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};

    // Validate name
    const trimmedName = formData.name.trim();
    if (!trimmedName) {
      newErrors.name = 'Document name is required';
    } else if (trimmedName.length > 255) {
      newErrors.name = 'Document name must not exceed 255 characters';
    }

    // Validate required fields
    if (!formData.category_id) {
      newErrors.category_id = 'Category is required';
    }
    if (!formData.subcategory_id) {
      newErrors.subcategory_id = 'Subcategory is required';
    }
    if (!formData.stage_id) {
      newErrors.stage_id = 'Stage is required';
    }
    if (!formData.assigned_to) {
      newErrors.assigned_to = 'Assigned user is required';
    }

    // File is only required for creation
    if (!isEditing && !selectedFile) {
      newErrors.file = 'Document file is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);
    setApiError(null);

    try {
      if (isEditing && document) {
        const updateData: DocumentUpdateInput = {
          name: formData.name.trim(),
          category_id: formData.category_id,
          subcategory_id: formData.subcategory_id,
          stage_id: formData.stage_id,
          assigned_to: formData.assigned_to,
          description: formData.description.trim() || undefined,
          tag_ids: formData.tag_ids.length > 0 ? formData.tag_ids : undefined,
        };
        await (updateFn ?? api.updateDocument.bind(api))(document.id, updateData);
      } else {
        const createData: DocumentCreateInput = {
          name: formData.name.trim(),
          category_id: formData.category_id,
          subcategory_id: formData.subcategory_id,
          stage_id: formData.stage_id,
          assigned_to: formData.assigned_to,
          document: selectedFile!,
          description: formData.description.trim() || undefined,
          tag_ids: formData.tag_ids.length > 0 ? formData.tag_ids : undefined,
        };
        await api.createDocument(createData);
      }
      onSuccess();
      onClose();
    } catch (err) {
      const error = err as ApiError;
      setApiError(error.detail || 'Failed to save document');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  const categoryOptions = [
    { value: '', label: 'Select a category' },
    ...categories.map((category) => ({
      value: category.id,
      label: category.title,
    })),
  ];

  const subcategoryOptions = [
    { value: '', label: 'Select a subcategory' },
    ...subcategories.map((subcategory) => ({
      value: subcategory.id,
      label: subcategory.title,
    })),
  ];

  const stageOptions = [
    { value: '', label: 'Select a stage' },
    ...stages.map((stage) => ({
      value: stage.id,
      label: stage.title,
    })),
  ];

  const userOptions = [
    { value: '', label: 'Unassigned' },
    ...users.map((user) => ({
      value: user.id,
      label: user.username,
    })),
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEditing ? 'Edit Document' : 'Create Document'}
      size="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {apiError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm">
            {apiError}
          </div>
        )}

        {isLoadingData ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            <p className="mt-2 text-gray-500">Loading form data...</p>
          </div>
        ) : (
          <div className="space-y-4">
            <Input
              label="Document Name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              error={errors.name}
              placeholder="e.g., Project Proposal Q1 2024"
              required
              maxLength={255}
            />

            {!isEditing && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Document File <span className="text-red-500">*</span>
                </label>
                <input
                  type="file"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    setSelectedFile(file || null);
                    if (errors.file) {
                      setErrors((prev) => ({ ...prev, file: '' }));
                    }
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-black focus:border-black file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-black file:text-white hover:file:bg-gray-800"
                />
                {selectedFile && (
                  <p className="mt-1 text-sm text-gray-500">
                    Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(2)} KB)
                  </p>
                )}
                {errors.file && (
                  <p className="mt-1 text-sm text-red-600">{errors.file}</p>
                )}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category <span className="text-red-500">*</span>
                </label>
                <Select
                  value={formData.category_id}
                  onChange={(e) => handleChange('category_id', e.target.value)}
                  options={categoryOptions}
                />
                {errors.category_id && (
                  <p className="mt-1 text-sm text-red-600">{errors.category_id}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Subcategory <span className="text-red-500">*</span>
                </label>
                <Select
                  value={formData.subcategory_id}
                  onChange={(e) => handleChange('subcategory_id', e.target.value)}
                  options={subcategoryOptions}
                  disabled={!formData.category_id}
                />
                {errors.subcategory_id && (
                  <p className="mt-1 text-sm text-red-600">{errors.subcategory_id}</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Stage <span className="text-red-500">*</span>
                </label>
                <Select
                  value={formData.stage_id}
                  onChange={(e) => handleChange('stage_id', e.target.value)}
                  options={stageOptions}
                />
                {errors.stage_id && (
                  <p className="mt-1 text-sm text-red-600">{errors.stage_id}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Assigned To <span className="text-red-500">*</span>
                </label>
                <Select
                  value={formData.assigned_to}
                  onChange={(e) => handleChange('assigned_to', e.target.value)}
                  options={userOptions}
                />
                {errors.assigned_to && (
                  <p className="mt-1 text-sm text-red-600">{errors.assigned_to}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Enter document description..."
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-black focus:border-black"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Tags
              </label>
              <div className="border border-gray-300 rounded-md p-2 min-h-[42px] max-h-32 overflow-y-auto">
                {tags.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {tags.map((tag) => (
                      <label
                        key={tag.id}
                        className="inline-flex items-center cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={formData.tag_ids.includes(tag.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setFormData((prev) => ({
                                ...prev,
                                tag_ids: [...prev.tag_ids, tag.id],
                              }));
                            } else {
                              setFormData((prev) => ({
                                ...prev,
                                tag_ids: prev.tag_ids.filter((id) => id !== tag.id),
                              }));
                            }
                          }}
                          className="sr-only"
                        />
                        <span
                          className={`inline-flex items-center px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                            formData.tag_ids.includes(tag.id)
                              ? 'bg-black text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          {tag.title}
                        </span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No tags available</p>
                )}
              </div>
              {formData.tag_ids.length > 0 && (
                <p className="mt-1 text-sm text-gray-500">
                  {formData.tag_ids.length} tag{formData.tag_ids.length !== 1 ? 's' : ''} selected
                </p>
              )}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-3 pt-4 border-t">
          <Button
            type="button"
            variant="secondary"
            onClick={onClose}
            disabled={isLoading || isLoadingData}
          >
            Cancel
          </Button>
          <Button type="submit" isLoading={isLoading} disabled={isLoadingData}>
            {isEditing ? 'Update Document' : 'Create Document'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}