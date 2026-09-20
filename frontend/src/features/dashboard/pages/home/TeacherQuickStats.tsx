import React from 'react';
import { AlertCircle, BookOpen, Calendar, FlaskConical } from 'lucide-react';
import { StatCard } from '@/components/shared/StatCard';

export const TeacherQuickStats = () => (
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <StatCard
      title="Assigned Courses"
      value="04 COURSES"
      icon={<BookOpen className="h-5 w-5" />}
      subtitle="Current academic term"
      tag="LOAD // FACULTY"
      accentColor="cyan"
    />
    <StatCard
      title="Today's Sessions"
      value="03 CLASSES"
      icon={<Calendar className="h-5 w-5" />}
      subtitle="Next: EEE 312 at 11:00"
      tag="SCHEDULE // TODAY"
      accentColor="cyan"
    />
    <StatCard
      title="Pending Submissions"
      value="12 TO REVIEW"
      icon={<AlertCircle className="h-5 w-5" />}
      subtitle="Assignments and projects"
      tag="QUEUE // REVIEW"
      accentColor="crimson"
    />
    <StatCard
      title="Lab Requests"
      value="02 PENDING"
      icon={<FlaskConical className="h-5 w-5" />}
      subtitle="Access and equipment"
      tag="QUEUE // LAB"
      accentColor="cyan"
    />
  </div>
);