import { describe, expect, it } from '@jest/globals';

import {
  dayIndex,
  dayName,
  formatTimeRange,
  groupRoutineByDay,
  sortRoutine,
  timeToMinutes,
  todayRoutine,
} from '../routine';
import type { RoutineEntry } from '../../types';

function entry(overrides: Partial<RoutineEntry>): RoutineEntry {
  return {
    id: 'entry-1',
    course_code: 'EEE 311',
    course_title: 'Digital Signal Processing',
    day_of_week: 'Sunday',
    start_time: '10:00 AM',
    end_time: '11:30 AM',
    room_number: 'EEE-201',
    instructor_name: 'Dr. Rahman',
    is_lab: false,
    ...overrides,
  };
}

describe('dayIndex', () => {
  it('orders the week from Sunday, matching the Bangladeshi academic week', () => {
    expect(dayIndex('Sunday')).toBe(0);
    expect(dayIndex('Thursday')).toBe(4);
    expect(dayIndex('Saturday')).toBe(6);
  });

  it('is case- and whitespace-insensitive', () => {
    expect(dayIndex('  monday ')).toBe(1);
  });

  it('sorts unknown days last instead of first', () => {
    expect(dayIndex('Funday')).toBe(7);
  });
});

describe('timeToMinutes', () => {
  it('parses the 12-hour strings the API returns', () => {
    expect(timeToMinutes('10:00 AM')).toBe(600);
    expect(timeToMinutes('12:05 PM')).toBe(725);
    expect(timeToMinutes('12:00 AM')).toBe(0);
    expect(timeToMinutes('11:59 PM')).toBe(1439);
  });

  it('parses 24-hour strings', () => {
    expect(timeToMinutes('14:30')).toBe(870);
  });

  it('pushes unparseable or missing times to the end', () => {
    expect(timeToMinutes(null)).toBe(Number.MAX_SAFE_INTEGER);
    expect(timeToMinutes('noon')).toBe(Number.MAX_SAFE_INTEGER);
  });
});

describe('sortRoutine', () => {
  it('sorts by weekday then start time, and does not mutate the input', () => {
    const input = [
      entry({ id: 'wed', day_of_week: 'Wednesday' }),
      entry({ id: 'sun-late', day_of_week: 'Sunday', start_time: '02:00 PM' }),
      entry({ id: 'sun-early', day_of_week: 'Sunday', start_time: '09:15 AM' }),
    ];

    expect(sortRoutine(input).map((item) => item.id)).toEqual(['sun-early', 'sun-late', 'wed']);
    expect(input.map((item) => item.id)).toEqual(['wed', 'sun-late', 'sun-early']);
  });
});

describe('groupRoutineByDay', () => {
  it('groups into week order with sorted entries inside each day', () => {
    const groups = groupRoutineByDay([
      entry({ id: 'tue', day_of_week: 'Tuesday' }),
      entry({ id: 'sun-b', day_of_week: 'Sunday', start_time: '01:00 PM' }),
      entry({ id: 'sun-a', day_of_week: 'Sunday', start_time: '08:00 AM' }),
    ]);

    expect(groups.map((group) => group.day)).toEqual(['Sunday', 'Tuesday']);
    expect(groups[0].entries.map((item) => item.id)).toEqual(['sun-a', 'sun-b']);
  });

  it('returns an empty list for an empty routine', () => {
    expect(groupRoutineByDay([])).toEqual([]);
  });
});

describe('dayName and todayRoutine', () => {
  it('derives the full day name from a date', () => {
    // 2026-11-02 is a Monday.
    expect(dayName(new Date(2026, 10, 2))).toBe('Monday');
  });

  it("returns only today's classes in start-time order", () => {
    const routine = [
      entry({ id: 'mon-late', day_of_week: 'Monday', start_time: '03:00 PM' }),
      entry({ id: 'mon-early', day_of_week: 'Monday', start_time: '08:00 AM' }),
      entry({ id: 'tue', day_of_week: 'Tuesday' }),
    ];

    expect(todayRoutine(routine, new Date(2026, 10, 2)).map((item) => item.id)).toEqual([
      'mon-early',
      'mon-late',
    ]);
  });
});

describe('formatTimeRange', () => {
  it('renders a range, a single time, or a placeholder', () => {
    expect(formatTimeRange('10:00 AM', '11:30 AM')).toBe('10:00 AM – 11:30 AM');
    expect(formatTimeRange('10:00 AM', null)).toBe('10:00 AM');
    expect(formatTimeRange(null, null)).toBe('Time not set');
  });
});
