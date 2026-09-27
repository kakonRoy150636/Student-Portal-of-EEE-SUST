import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { flattenNav } from '@/layouts/nav';
import { useAuth } from '@/contexts/AuthContext';

export const CommandSearch = ({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) => {
  const { role } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const items = useMemo(() => flattenNav(role), [role]);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) =>
      [item.name, item.hint, item.path].filter(Boolean).some((value) => value!.toLowerCase().includes(q)),
    );
  }, [items, query]);

  useEffect(() => {
    if (!open) setQuery('');
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="p-0 overflow-hidden">
        <DialogTitle className="sr-only">Search the portal</DialogTitle>
        <div className="flex items-center gap-2 border-b border-[var(--border)] px-4">
          <Search className="h-4 w-4 text-[var(--text-muted)]" />
          <input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search pages…"
            className="h-12 w-full bg-transparent text-sm text-[var(--text)] outline-none placeholder:text-[var(--text-subtle)]"
            aria-label="Search pages"
          />
        </div>
        <ul className="max-h-80 overflow-y-auto p-2">
          {results.length === 0 ? (
            <li className="px-3 py-6 text-center text-sm text-[var(--text-muted)]">No matching pages.</li>
          ) : (
            results.map((item) => (
              <li key={item.path + item.name}>
                <button
                  type="button"
                  onClick={() => {
                    navigate(item.path);
                    onOpenChange(false);
                  }}
                  className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left hover:bg-[var(--surface-muted)]"
                >
                  <item.icon className="h-4 w-4 text-[var(--text-muted)]" />
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-[var(--text)]">{item.name}</span>
                    {item.hint && <span className="block text-xs text-[var(--text-muted)]">{item.hint}</span>}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      </DialogContent>
    </Dialog>
  );
};
