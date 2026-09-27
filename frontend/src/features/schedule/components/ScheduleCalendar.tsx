import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ClassSchedule } from '@/types/academic';

export const ScheduleCalendar = ({
  days,
  classes,
}: {
  days: string[];
  classes: ClassSchedule[];
}) => (
  <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
    {days.map((day) => {
      const items = classes.filter((item) => item.day_of_week === day);
      return (
        <div key={day} className="space-y-2">
          <div className="rounded-lg bg-[var(--surface-muted)] px-2 py-2 text-center text-xs font-bold uppercase tracking-wide text-[var(--text-muted)]">
            {day}
          </div>
          {items.length === 0 ? (
            <p className="rounded-xl border border-dashed border-[var(--border)] px-3 py-6 text-center text-xs text-[var(--text-subtle)]">
              No class
            </p>
          ) : (
            items.map((item) => (
              <Card key={item.id} className="border-l-4 border-l-[var(--accent)]">
                <CardHeader className="p-3 pb-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-[var(--text)]">{item.course_code}</span>
                    {item.is_lab && <Badge variant="secondary">Lab</Badge>}
                  </div>
                  <CardTitle className="text-xs font-medium text-[var(--text-muted)]">
                    {item.start_time} – {item.end_time}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 p-3 pt-0 text-xs text-[var(--text-muted)]">
                  <p className="text-[var(--text)]">{item.course_title}</p>
                  <p>{item.room_number}</p>
                  <p>{item.instructor_name}</p>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      );
    })}
  </div>
);
