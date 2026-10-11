import type { ClassSchedule } from '@/types/academic';

export type OfflineClass = Omit<ClassSchedule, 'instructor_name'>;
export type RoutineSnapshot = { owner: string; savedAt: string; classes: OfflineClass[] };
const DB = 'portal-offline';
const STORE = 'routine';
let activeOwner: string | null = null;

async function transact<T>(operation: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    const open = indexedDB.open(DB, 1);
    open.onupgradeneeded = () => open.result.createObjectStore(STORE);
    open.onerror = () => reject(open.error);
    open.onsuccess = () => {
      const db = open.result;
      const tx = db.transaction(STORE, 'readwrite');
      const request = operation(tx.objectStore(STORE));
      tx.oncomplete = () => { db.close(); resolve(request.result); };
      tx.onabort = () => { db.close(); reject(tx.error); };
      tx.onerror = () => { db.close(); reject(tx.error); };
    };
  });
}

export async function saveRoutine(owner: string, classes: ClassSchedule[]) {
  // AuthContext selects the owner before publishing a user.  Refuse writes
  // after logout/account-switch cleanup so a late schedule query cannot put a
  // previous user's routine back into IndexedDB.
  if (activeOwner !== owner) return;
  const snapshot: RoutineSnapshot = {
    owner, savedAt: new Date().toISOString(),
    classes: classes.map(({ id, course_code, course_title, day_of_week, start_time, end_time, room_number, is_lab }) =>
      ({ id, course_code, course_title, day_of_week, start_time, end_time, room_number, is_lab })),
  };
  await transact((store) => activeOwner === owner
    ? store.put(snapshot, 'last')
    : store.get('__offline_write_cancelled__'));
}
export const readRoutine = () => transact<RoutineSnapshot | undefined>((store) => store.get('last'));
export const clearRoutine = () => {
  activeOwner = null;
  return transact((store) => store.clear());
};

export async function selectRoutineOwner(owner: string) {
  activeOwner = owner;
  const stored = await readRoutine();
  if (stored && stored.owner !== owner) {
    await clearRoutine();
    activeOwner = owner;
  }
}
