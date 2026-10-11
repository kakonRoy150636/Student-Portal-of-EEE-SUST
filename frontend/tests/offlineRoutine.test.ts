import 'fake-indexeddb/auto';
import { afterEach, it, expect } from 'vitest';
import { saveRoutine, readRoutine, selectRoutineOwner, clearRoutine } from '../src/lib/offlineRoutine';
afterEach(clearRoutine);
it('stores routine without teacher/personal information and clears on account switch', async () => {
  await selectRoutineOwner('first');
  await saveRoutine('first', [{ id: 'schedule', course_code: 'EEE101', course_title: 'Circuits',
    day_of_week: 'Monday', start_time: '10:00', end_time: '11:00', room_number: '201',
    instructor_name: 'Private Name', is_lab: false }]);
  const saved = await readRoutine();
  expect(saved?.classes[0].course_code).toBe('EEE101');
  expect(JSON.stringify(saved)).not.toContain('Private Name');
  expect(await readRoutine()).toBeDefined();
  await selectRoutineOwner('second');
  expect(await readRoutine()).toBeUndefined();
});
it('logout can delete the saved snapshot', async () => {
  await selectRoutineOwner('first');
  await saveRoutine('first', []);
  await clearRoutine();
  expect(await readRoutine()).toBeUndefined();
});

it('does not restore a late routine write after logout cleanup starts', async () => {
  await selectRoutineOwner('first');
  const lateWrite = saveRoutine('first', [{ id: 'schedule', course_code: 'EEE101', course_title: 'Circuits',
    day_of_week: 'Monday', start_time: '10:00', end_time: '11:00', room_number: '201',
    instructor_name: 'Private Name', is_lab: false }]);
  await clearRoutine();
  await lateWrite;
  expect(await readRoutine()).toBeUndefined();
});
