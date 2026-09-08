import React from 'react';
import { Clock, MapPin, User, Terminal } from 'lucide-react';

export const TodayRoutine = () => {
  const lectures = [
    {
      id: '0x01',
      code: 'EEE 311',
      title: 'Electrical Machines II',
      time: '09:00 - 10:30 AM',
      room: 'IICT // ROOM 304',
      instructor: 'DR. M. RAHMAN',
      status: 'live'
    },
    {
      id: '0x02',
      code: 'EEE 313',
      title: 'Microprocessor & Interfacing',
      time: '11:00 - 12:30 PM',
      room: 'DEPT // MICRO LAB 2',
      instructor: 'ENGR. K. AHMED',
      status: 'queued'
    }
  ];

  return (
    <div className="hud-box corner-brackets rounded-xl p-5 flex flex-col justify-between">
      <div>
        {/* লিনাক্স টার্মিনাল হেডার */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 font-mono text-xs">
          <div className="flex items-center gap-2">
            <div className="flex gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#FF1E56]" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#00F0FF]" />
            </div>
            <span className="text-slate-400 flex items-center gap-1 ml-2 font-mono text-[11px]">
              <Terminal className="h-3.5 w-3.5 text-cyan-400" />
              sust@eee-node:~/telemetry/schedule
            </span>
          </div>
          <span className="text-[10px] text-[#00F0FF] tracking-wider uppercase font-semibold">
            STATUS: 2 ACTIVE SLOTS
          </span>
        </div>

        {/* ক্লাস স্লট */}
        <div className="mt-4 space-y-3">
          {lectures.map((lec) => {
            const isLive = lec.status === 'live';
            return (
              <div
                key={lec.id}
                className={`relative rounded-lg border p-4 transition-all ${
                  isLive
                    ? 'border-[#FF1E56]/50 bg-[#FF1E56]/[0.06] shadow-[0_0_15px_rgba(255,30,86,0.15)]'
                    : 'border-slate-800/80 bg-slate-900/40 hover:border-cyan-500/30'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 font-mono text-xs">
                      <span className="font-black text-[#00F0FF]">{lec.code}</span>
                      {isLive ? (
                        <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-bold bg-[#FF1E56]/20 text-[#FF1E56] border border-[#FF1E56]/40">
                          <span className="h-1.5 w-1.5 rounded-full bg-[#FF1E56] animate-ping" />
                          TRANSMITTING NOW
                        </span>
                      ) : (
                        <span className="rounded px-1.5 py-0.5 text-[9px] font-mono text-slate-400 border border-slate-700 bg-slate-800/60">
                          QUEUED
                        </span>
                      )}
                    </div>
                    <h4 className="mt-1 font-bold text-sm text-slate-100">{lec.title}</h4>
                  </div>

                  <div className="flex items-center gap-1 text-xs font-mono text-slate-400">
                    <Clock className="h-3.5 w-3.5 text-cyan-400" />
                    <span>{lec.time}</span>
                  </div>
                </div>

                <div className="mt-3 flex items-center gap-5 text-xs font-mono text-slate-400 border-t border-slate-800/60 pt-2.5">
                  <div className="flex items-center gap-1.5">
                    <MapPin className="h-3.5 w-3.5 text-slate-500" />
                    <span className="text-slate-300">{lec.room}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <User className="h-3.5 w-3.5 text-slate-500" />
                    <span className="text-slate-300">{lec.instructor}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] font-mono text-slate-500 flex justify-between">
        <span>LAST_PING: 0.14ms</span>
        <span className="text-cyan-400">CR_BROADCAST: ACTIVE</span>
      </div>
    </div>
  );
};