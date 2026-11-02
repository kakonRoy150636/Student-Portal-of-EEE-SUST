import { describe, expect, it } from '@jest/globals';

import { summarizeDashboard } from '../dashboard';
import type { DashboardSummary, StudentSummary } from '../../types';

function studentSummary(overrides: Partial<StudentSummary> = {}): StudentSummary {
  return {
    enrolled_courses: 5,
    total_classes: 40,
    attended: 35,
    attendance_percentage: 87.5,
    below_attendance_threshold: false,
    credit_hours: 15,
    today_classes: 2,
    routine: [
      {
        course_code: 'EEE 311',
        course_title: 'Digital Signal Processing',
        day_of_week: 'Monday',
        start_time: '10:00 AM',
        end_time: '11:30 AM',
        room_number: 'EEE-201',
        building: 'Academic Building',
      },
    ],
    unread_notifications: 3,
    opportunities: 4,
    ...overrides,
  };
}

function summary(overrides: Partial<DashboardSummary>): DashboardSummary {
  return {
    role: 'student',
    student: null,
    teacher: null,
    er: null,
    alumni: null,
    admin: null,
    ...overrides,
  };
}

describe('summarizeDashboard', () => {
  it('returns an empty view when the summary has not loaded', () => {
    expect(summarizeDashboard(undefined).tiles).toEqual([]);
  });

  it('builds student tiles from the student section', () => {
    const view = summarizeDashboard(summary({ role: 'student', student: studentSummary() }));

    expect(view.unreadNotifications).toBe(3);
    expect(view.todayClasses).toHaveLength(1);
    expect(view.tiles.map((tile) => tile.key)).toEqual(['attendance', 'courses', 'today', 'opportunities']);
    expect(view.tiles[0].value).toBe('87.5%');
    expect(view.tiles[0].warning).toBe(false);
  });

  it('flags attendance below the 75% threshold', () => {
    const view = summarizeDashboard(
      summary({
        role: 'student',
        student: studentSummary({ attendance_percentage: 62, below_attendance_threshold: true }),
      }),
    );

    expect(view.tiles[0].warning).toBe(true);
    expect(view.tiles[0].hint).toBe('Below the 75% threshold');
  });

  it('shows "no classes recorded" rather than 0% when attendance is null', () => {
    const view = summarizeDashboard(
      summary({
        role: 'student',
        student: studentSummary({
          attendance_percentage: null,
          below_attendance_threshold: null,
          total_classes: 0,
          attended: 0,
        }),
      }),
    );

    expect(view.tiles[0].value).toBe('—');
    expect(view.tiles[0].hint).toBe('No classes recorded yet');
    expect(view.tiles[0].warning).toBe(false);
  });

  it('treats a CR account as a student', () => {
    const view = summarizeDashboard(summary({ role: 'cr', student: studentSummary() }));
    expect(view.tiles).toHaveLength(4);
    expect(view.todayClasses).toHaveLength(1);
  });

  it('never leaks another role section into the tiles', () => {
    const view = summarizeDashboard(
      summary({
        role: 'teacher',
        student: studentSummary(),
        teacher: {
          assigned_courses: 3,
          students_taught: 120,
          today_classes: 1,
          pending_equipment_requests: 2,
          pending_room_requests: 1,
          pending_project_proposals: 0,
          unread_notifications: 5,
        },
      }),
    );

    expect(view.tiles.map((tile) => tile.key)).toEqual(['assigned', 'students', 'today', 'requests']);
    expect(view.tiles[0].value).toBe('3');
    expect(view.todayClasses).toEqual([]);
  });

  it('shows a missing section as empty instead of inventing values', () => {
    const view = summarizeDashboard(summary({ role: 'super_admin', admin: null }));
    expect(view.tiles).toEqual([]);
    expect(view.unreadNotifications).toBe(0);
  });

  it('sums the teacher pending queues into one tile', () => {
    const view = summarizeDashboard(
      summary({
        role: 'teacher',
        teacher: {
          assigned_courses: 1,
          students_taught: 10,
          today_classes: 0,
          pending_equipment_requests: 2,
          pending_room_requests: 3,
          pending_project_proposals: 4,
          unread_notifications: 0,
        },
      }),
    );

    const requests = view.tiles.find((tile) => tile.key === 'requests');
    expect(requests?.value).toBe('9');
  });
});
