export interface Course {
  id: string;
  course_code: string;
  title: string;
  credit_hours: number;
  type: string;
}

export interface Semester {
  id: number;
  title: string;
  is_active: boolean;
}

export interface ClassSchedule {
  id: string;
  course_code: string;
  course_title: string;
  day_of_week: string;
  start_time: string;
  end_time: string;
  room_number: string;
  instructor_name: string;
  is_lab: boolean;
}
