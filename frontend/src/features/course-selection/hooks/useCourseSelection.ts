import { isAxiosError } from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { UserRole } from '@/types/auth';
import type { CourseEnrollment, CourseOffering, Semester } from '@/types/academic';
import { courseSelectionApi } from '../api/courseSelectionApi';

export type SelectionAction = 'select' | 'drop' | 'reselect';
export type SelectionMutation = { action: SelectionAction; offeringId: string };

export interface CourseSelectionSnapshot {
  semesters: Semester[];
  offerings: CourseOffering[];
  enrollments: CourseEnrollment[];
  activeCreditTotal: number;
}

export function isOfferingSelectable(offering: CourseOffering | undefined, semesters: Semester[]): boolean {
  return Boolean(offering?.publication_status === 'published' && offering.semester_is_active &&
    semesters.some((semester) => semester.id === offering.semester_id && semester.is_active));
}

export function isSelectionConflict(error: unknown): boolean {
  return isAxiosError(error) && error.response?.status === 409;
}

export function useCourseSelection() {
  const { user } = useAuth();
  const client = useQueryClient();
  const queryKey = ['course-offerings', 'student-selection', user?.id];
  const allowed = user?.role === UserRole.STUDENT || user?.role === UserRole.CR;
  const query = useQuery({
    queryKey,
    enabled: allowed,
    retry: false,
    queryFn: async ({ signal }): Promise<CourseSelectionSnapshot> => {
      const [semesters, offerings, enrollments, credits] = await Promise.all([
        courseSelectionApi.getActiveSemesters(signal),
        courseSelectionApi.getPublishedOfferings(signal),
        courseSelectionApi.getMyEnrollments(signal),
        courseSelectionApi.getActiveCredits(signal),
      ]);
      return {
        semesters: semesters.data,
        offerings: offerings.data,
        enrollments: enrollments.data.filter((enrollment) => enrollment.student_id === user?.id),
        activeCreditTotal: credits.data.active_credit_total,
      };
    },
  });

  const mutation = useMutation({
    retry: false,
    mutationFn: async ({ action, offeringId }: SelectionMutation) => {
      const snapshot = query.data;
      const offering = snapshot?.offerings.find((item) => item.id === offeringId);
      if (!allowed || !snapshot || !isOfferingSelectable(offering, snapshot.semesters)) {
        throw new Error('This offering is not published in an active semester. Refresh the course list.');
      }
      const enrollment = snapshot.enrollments.find((item) => item.course_offering_id === offeringId);
      if (action === 'select' && !enrollment) return (await courseSelectionApi.select(offeringId)).data;
      if (action === 'drop' && enrollment && enrollment.status !== 'drop') {
        return (await courseSelectionApi.drop(enrollment.id)).data;
      }
      if (action === 'reselect' && enrollment?.status === 'drop') {
        return (await courseSelectionApi.reselect(enrollment.id)).data;
      }
      throw new Error('The enrollment state changed. Refresh the course list before trying again.');
    },
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey }),
        client.invalidateQueries({ queryKey: ['dashboard'] }),
        client.invalidateQueries({ queryKey: ['schedules'] }),
        client.invalidateQueries({ queryKey: ['attendance'] }),
        client.invalidateQueries({ queryKey: ['notifications'] }),
      ]);
    },
    onError: async (error) => {
      if (isSelectionConflict(error)) await client.invalidateQueries({ queryKey });
    },
  });

  return { query, mutation };
}
