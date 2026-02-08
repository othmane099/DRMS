import React from 'react';

interface TabProps {
  label: string;
  isActive: boolean;
  onClick: () => void;
}

const Tab: React.FC<TabProps> = ({ label, isActive, onClick }) => {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 font-medium text-sm transition-colors relative ${
        isActive
          ? 'text-blue-600 border-b-2 border-blue-600'
          : 'text-gray-500 hover:text-gray-700 border-b-2 border-transparent'
      }`}
    >
      {label}
    </button>
  );
};

interface TabsProps {
  tabs: {
    key: string;
    label: string;
  }[];
  activeTab: string;
  onTabChange: (key: string) => void;
  children: React.ReactNode;
}

export const Tabs: React.FC<TabsProps> = ({ tabs, activeTab, onTabChange, children }) => {
  return (
    <div>
      <div className="border-b border-gray-200">
        <div className="flex space-x-4">
          {tabs.map((tab) => (
            <Tab
              key={tab.key}
              label={tab.label}
              isActive={activeTab === tab.key}
              onClick={() => onTabChange(tab.key)}
            />
          ))}
        </div>
      </div>
      <div className="mt-6">{children}</div>
    </div>
  );
};