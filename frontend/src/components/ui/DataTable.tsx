// src/components/ui/DataTable.tsx
import React from 'react';

interface Column<T> {
  header: string;
  accessor: keyof T | ((row: T) => React.ReactNode);
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  emptyMessage?: string;
}

export function DataTable<T extends object>({ columns, data, loading = false, emptyMessage = 'No data available.' }: DataTableProps<T>) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-4 text-text-secondary">
        Loading…
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center py-4 text-text-muted">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left font-body-table">
        <thead className="bg-surface-bright">
          <tr>
            {columns.map((col, idx) => (
              <th
                key={idx}
                className={`px-4 py-3 border-b text-text-muted font-label-sm uppercase ${col.className || ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border-base">
          {data.map((row, rowIdx) => (
            <tr key={rowIdx} className="hover:bg-surface-secondary/50">
              {columns.map((col, colIdx) => {
                const value =
                  typeof col.accessor === 'function'
                    ? col.accessor(row)
                    : (row[col.accessor as keyof T] as unknown);
                return (
                  <td key={colIdx} className={`px-4 py-3 ${col.className || ''}`}>
                    {value as React.ReactNode}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;
