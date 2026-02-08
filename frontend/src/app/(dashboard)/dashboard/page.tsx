'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { Card, CardHeader, Spinner, Toast } from '@/components/ui';
import { api } from '@/lib/api';
import { DashboardResponse, DashboardReminder, ApiError } from '@/types';
import {usePermissions} from "@/hooks/usePermissions";

// --- Constants ---

const PIE_COLORS = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];

type AgendaView = 'day' | 'week' | 'month';
type MyAgendaView = 'day' | 'week' | 'month';

// --- Utility Functions ---

function toDateString(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function parseLocalDate(str: string): Date {
  const [y, m, d] = str.split('-').map(Number);
  return new Date(y, m - 1, d);
}

function getWeekStart(date: Date): Date {
  const d = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  d.setDate(d.getDate() - (d.getDay() === 0 ? 6 : d.getDay() - 1));
  return d;
}

function formatTime(time: string): string {
  const [h, m] = time.split(':').map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h >= 12 ? 'PM' : 'AM'}`;
}

function formatAgendaDate(dateStr: string): string {
  const date = parseLocalDate(dateStr);
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
}

// --- SVG Pie Chart Helpers ---

function polarToXY(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arcSlicePath(cx: number, cy: number, r: number, startAngle: number, sweep: number): string {
  const p1 = polarToXY(cx, cy, r, startAngle);
  const p2 = polarToXY(cx, cy, r, startAngle + sweep);
  const large = sweep > 180 ? 1 : 0;
  return `M ${cx} ${cy} L ${p1.x} ${p1.y} A ${r} ${r} 0 ${large} 1 ${p2.x} ${p2.y} Z`;
}

// --- Pie Chart Component ---

function PieChart({ items, size = 160 }: { items: { label: string; count: number }[]; size?: number }) {
  const total = items.reduce((s, i) => s + i.count, 0);

  if (total === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-sm text-gray-400">No data</p>
      </div>
    );
  }

  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2 - 2;

  let angle = 0;
  const slices = items.map((item, i) => {
    const sweep = (item.count / total) * 360;
    const startAngle = angle;
    angle += sweep;
    return { ...item, sweep, startAngle, color: PIE_COLORS[i % PIE_COLORS.length] };
  });

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {items.length === 1 ? (
          <circle cx={cx} cy={cy} r={r} fill={slices[0].color} />
        ) : (
          slices.map((s, i) => (
            <path key={i} d={arcSlicePath(cx, cy, r, s.startAngle, s.sweep)} fill={s.color} stroke="white" strokeWidth={2} />
          ))
        )}
      </svg>
      <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 justify-center">
        {slices.map((s, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ backgroundColor: s.color }} />
            <span className="text-xs text-gray-600">{s.label} ({s.count})</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Stat Card Component ---

function StatCard({ title, value, icon, colorClass }: { title: string; value: number; icon: React.ReactNode; colorClass: string }) {
  return (
    <Card padding="md">
      <div className="flex items-center gap-3">
        <div className={cn('p-2 rounded-lg', colorClass)}>
          {icon}
        </div>
        <div>
          <p className="text-2xl font-bold">{value}</p>
          <p className="text-xs text-gray-500">{title}</p>
        </div>
      </div>
    </Card>
  );
}

// --- Main Dashboard Page ---

export default function DashboardPage() {
  const { hasAnyPermission } = usePermissions();
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error'; visible: boolean }>({
    message: '',
    type: 'error',
    visible: false,
  });

  const [agendaView, setAgendaView] = useState<AgendaView>('week');
  const [agendaDate, setAgendaDate] = useState(() => new Date());
  const [myAgendaView, setMyAgendaView] = useState<MyAgendaView>('week');
  const [myAgendaDate, setMyAgendaDate] = useState(() => new Date());

  const showToast = useCallback((message: string, type: 'success' | 'error' = 'error') => {
    setToast({ message, type, visible: true });
  }, []);

  const canCreateUsers = hasAnyPermission(['users.create']);
  const canCreateDocument = hasAnyPermission(['documents.create']);
  const canCreateCategory = hasAnyPermission(['categories.create']);
  const canCreateSubcategory = hasAnyPermission(['subcategories.create']);
  const canCreateReminder = hasAnyPermission(['reminders.create']);

  useEffect(() => {
    setIsLoading(true);
    api
      .getDashboard()
      .then(setDashboard)
      .catch((err: ApiError) => showToast(err.detail || 'Failed to load dashboard'))
      .finally(() => setIsLoading(false));
  }, [showToast]);

  // --- Agenda date range & label ---

  const agendaRange = (() => {
    switch (agendaView) {
      case 'day': {
        const s = toDateString(agendaDate);
        return {
          start: s,
          end: s,
          label: agendaDate.toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            year: 'numeric',
          }),
        };
      }
      case 'week': {
        const ws = getWeekStart(agendaDate);
        const we = new Date(ws);
        we.setDate(we.getDate() + 6);
        return {
          start: toDateString(ws),
          end: toDateString(we),
          label: `${ws.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${we.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`,
        };
      }
      case 'month': {
        const ms = new Date(agendaDate.getFullYear(), agendaDate.getMonth(), 1);
        const me = new Date(agendaDate.getFullYear(), agendaDate.getMonth() + 1, 0);
        return {
          start: toDateString(ms),
          end: toDateString(me),
          label: agendaDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
        };
      }
    }
  })();

  const myAgendaRange = (() => {
    switch (myAgendaView) {
      case 'day': {
        const s = toDateString(myAgendaDate);
        return {
          start: s,
          end: s,
          label: myAgendaDate.toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            year: 'numeric',
          }),
        };
      }
      case 'week': {
        const ws = getWeekStart(myAgendaDate);
        const we = new Date(ws);
        we.setDate(we.getDate() + 6);
        return {
          start: toDateString(ws),
          end: toDateString(we),
          label: `${ws.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${we.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`,
        };
      }
      case 'month': {
        const ms = new Date(myAgendaDate.getFullYear(), myAgendaDate.getMonth(), 1);
        const me = new Date(myAgendaDate.getFullYear(), myAgendaDate.getMonth() + 1, 0);
        return {
          start: toDateString(ms),
          end: toDateString(me),
          label: myAgendaDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' }),
        };
      }
    }
  })();

  // Filter reminders client-side and group by date
  const filteredReminders = (dashboard?.reminders ?? []).filter(
    (r) => r.start >= agendaRange.start && r.start <= agendaRange.end
  );

  const myFilteredReminders = (dashboard?.my_reminders ?? []).filter(
      (r) => r.start >= myAgendaRange.start && r.start <= myAgendaRange.end
  );

  const grouped = filteredReminders.reduce<Record<string, DashboardReminder[]>>((acc, r) => {
    (acc[r.start] ??= []).push(r);
    return acc;
  }, {});

  const myGrouped = myFilteredReminders.reduce<Record<string, DashboardReminder[]>>((acc, r) => {
    (acc[r.start] ??= []).push(r);
    return acc;
  }, {});

  const sortedDates = Object.keys(grouped).sort();
  const mySortedDates = Object.keys(myGrouped).sort();
  const today = toDateString(new Date());

  // --- Agenda navigation ---

  const navigateAgenda = (dir: -1 | 1) => {
    setAgendaDate((prev) => {
      const d = new Date(prev);
      if (agendaView === 'day') d.setDate(d.getDate() + dir);
      else if (agendaView === 'week') d.setDate(d.getDate() + dir * 7);
      else {
        d.setDate(1);
        d.setMonth(d.getMonth() + dir);
      }
      return d;
    });
  };

  const navigateMyAgenda = (dir: -1 | 1) => {
    setMyAgendaDate((prev) => {
      const d = new Date(prev);
      if (myAgendaView === 'day') d.setDate(d.getDate() + dir);
      else if (myAgendaView === 'week') d.setDate(d.getDate() + dir * 7);
      else {
        d.setDate(1);
        d.setMonth(d.getMonth() + dir);
      }
      return d;
    });
  };

  // --- Render ---

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!dashboard) return null;

  return (
    <div className="space-y-6">
      <Toast
        message={toast.message}
        type={toast.type}
        isVisible={toast.visible}
        onClose={() => setToast((prev) => ({ ...prev, visible: false }))}
      />

      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Total Users and Categories - Top Row */}
      <div className="grid grid-cols-2 gap-4">
        {canCreateUsers && (
          <StatCard
            title="Total Users"
            value={dashboard.total_user}
            colorClass="bg-indigo-50"
            icon={
              <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            }
          />
        )}
        {canCreateCategory && (
          <StatCard
            title="Total Categories"
            value={dashboard.total_category}
            colorClass="bg-emerald-50"
            icon={
              <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            }
          />
        )}
      </div>

      {/* Other Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <StatCard
            title="My Total Documents"
            value={dashboard.my_total_document}
            colorClass="bg-blue-50"
            icon={
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            }
        />
        {canCreateDocument && (
          <StatCard
            title="Total Documents"
            value={dashboard.total_document}
            colorClass="bg-blue-50"
            icon={
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            }
          />
        )}
        <StatCard
            title="My Today's Documents"
            value={dashboard.my_today_document}
            colorClass="bg-cyan-50"
            icon={
              <svg className="w-5 h-5 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11v4m-2-2h4" />
              </svg>
            }
        />
        {canCreateDocument && (
          <StatCard
            title="Today's Documents"
            value={dashboard.today_document}
            colorClass="bg-cyan-50"
            icon={
              <svg className="w-5 h-5 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11v4m-2-2h4" />
              </svg>
            }
          />
        )}
        <StatCard
            title="My Total Reminders"
            value={dashboard.my_total_reminder}
            colorClass="bg-amber-50"
            icon={
              <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            }
        />
        {canCreateReminder && (
          <StatCard
            title="Total Reminders"
            value={dashboard.total_reminder}
            colorClass="bg-amber-50"
            icon={
              <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            }
          />
        )}
        <StatCard
            title="My Today's Reminders"
            value={dashboard.my_today_reminder}
            colorClass="bg-rose-50"
            icon={
              <svg className="w-5 h-5 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
        />
        {canCreateReminder && (
          <StatCard
            title="Today's Reminders"
            value={dashboard.today_reminder}
            colorClass="bg-rose-50"
            icon={
              <svg className="w-5 h-5 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />
        )}
      </div>

      {/* Pie Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {canCreateCategory && (
          <Card>
            <CardHeader title="Documents by Category" />
            <div className="flex justify-center">
              <PieChart items={dashboard.document_by_category.map((d) => ({ label: d.category, count: d.count }))} />
            </div>
          </Card>
        )}
        {canCreateSubcategory && (
          <Card>
            <CardHeader title="Documents by Subcategory" />
            <div className="flex justify-center">
              <PieChart items={dashboard.document_by_subcategory.map((d) => ({ label: d.subcategory, count: d.count }))} />
            </div>
          </Card>
        )}

      </div>

      {/* Agenda */}
      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
          <h2 className="text-lg font-semibold">My Agenda</h2>
          <div className="flex items-center gap-2">
            {/* View tabs */}
            <div className="flex border border-gray-200 rounded-md overflow-hidden">
              {(['day', 'week', 'month'] as MyAgendaView[]).map((view) => (
                  <button
                      key={view}
                      onClick={() => {
                        setMyAgendaView(view);
                        setMyAgendaDate(new Date());
                      }}
                      className={cn(
                          'px-3 py-1 text-sm capitalize transition-colors',
                          myAgendaView === view ? 'bg-black text-white' : 'text-gray-600 hover:bg-gray-100'
                      )}
                  >
                    {view}
                  </button>
              ))}
            </div>

            {/* Prev / Today / Next */}
            <button onClick={() => navigateMyAgenda(-1)} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <button
                onClick={() => setMyAgendaDate(new Date())}
                className="px-2.5 py-1 text-xs border border-gray-200 rounded-md hover:bg-gray-100 text-gray-600"
            >
              Today
            </button>
            <button onClick={() => navigateMyAgenda(1)} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-600">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>

        <p className="text-sm text-gray-500 mb-4">{myAgendaRange.label}</p>

        {mySortedDates.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">No reminders for this period.</p>
        ) : (
            <div className="space-y-4">
              {mySortedDates.map((date) => (
                  <div key={date}>
                    <p className={cn('text-sm font-semibold mb-2', date === today ? 'text-indigo-600' : 'text-gray-700')}>
                      {date === today ? 'Today' : formatAgendaDate(date)}
                    </p>
                    <div className="space-y-2">
                      {myGrouped[date].map((r) => (
                          <div
                              key={r.id}
                              className={cn('flex items-center gap-3 px-3 py-2 rounded-md', date === today ? 'bg-indigo-50' : 'bg-gray-50')}
                          >
                            <span className="text-xs text-gray-500 w-16 shrink-0">{formatTime(r.time)}</span>
                            <span className="text-sm text-gray-800">{r.title}</span>
                          </div>
                      ))}
                    </div>
                  </div>
              ))}
            </div>
        )}
      </Card>
      {canCreateReminder && (
        <Card>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
            <h2 className="text-lg font-semibold">Agenda</h2>
            <div className="flex items-center gap-2">
              {/* View tabs */}
              <div className="flex border border-gray-200 rounded-md overflow-hidden">
                {(['day', 'week', 'month'] as AgendaView[]).map((view) => (
                  <button
                    key={view}
                    onClick={() => {
                      setAgendaView(view);
                      setAgendaDate(new Date());
                    }}
                    className={cn(
                      'px-3 py-1 text-sm capitalize transition-colors',
                      agendaView === view ? 'bg-black text-white' : 'text-gray-600 hover:bg-gray-100'
                    )}
                  >
                    {view}
                  </button>
                ))}
              </div>

              {/* Prev / Today / Next */}
              <button onClick={() => navigateAgenda(-1)} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-600">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <button
                onClick={() => setAgendaDate(new Date())}
                className="px-2.5 py-1 text-xs border border-gray-200 rounded-md hover:bg-gray-100 text-gray-600"
              >
                Today
              </button>
              <button onClick={() => navigateAgenda(1)} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-600">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>

          <p className="text-sm text-gray-500 mb-4">{agendaRange.label}</p>

          {sortedDates.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">No reminders for this period.</p>
          ) : (
            <div className="space-y-4">
              {sortedDates.map((date) => (
                <div key={date}>
                  <p className={cn('text-sm font-semibold mb-2', date === today ? 'text-indigo-600' : 'text-gray-700')}>
                    {date === today ? 'Today' : formatAgendaDate(date)}
                  </p>
                  <div className="space-y-2">
                    {grouped[date].map((r) => (
                      <div
                        key={r.id}
                        className={cn('flex items-center gap-3 px-3 py-2 rounded-md', date === today ? 'bg-indigo-50' : 'bg-gray-50')}
                      >
                        <span className="text-xs text-gray-500 w-16 shrink-0">{formatTime(r.time)}</span>
                        <span className="text-sm text-gray-800">{r.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}