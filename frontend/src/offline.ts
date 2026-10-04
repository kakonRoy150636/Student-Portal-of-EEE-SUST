import './index.css';
import { readRoutine } from './lib/offlineRoutine';

void readRoutine().then((snapshot) => {
  document.getElementById('saved-at')!.textContent = snapshot
    ? `Saved ${new Date(snapshot.savedAt).toLocaleString('en-US', { timeZone: 'Asia/Dhaka' })} · Asia/Dhaka`
    : 'No routine saved yet. Open Class routine while online first.';
  for (const row of snapshot?.classes ?? []) {
    const card = document.createElement('article');
    card.className = 'surface space-y-1 p-4';
    const heading = document.createElement('h2');
    heading.textContent = `${row.course_code} · ${row.course_title}`;
    const time = document.createElement('p');
    time.textContent = `${row.day_of_week} ${row.start_time}–${row.end_time} · ${row.room_number}`;
    card.append(heading, time);
    document.getElementById('routine')!.append(card);
  }
  if (snapshot && !snapshot.classes.length) document.getElementById('routine')!.textContent = 'No classes published in your saved routine.';
}).catch(() => { document.getElementById('saved-at')!.textContent = 'Offline storage is unavailable on this device.'; });
