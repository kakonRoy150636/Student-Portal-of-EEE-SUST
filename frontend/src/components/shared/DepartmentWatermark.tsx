import React from 'react';

export const DepartmentWatermark = () => {
  return (
    <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden flex items-center justify-center">
      {/* গ্রিড ও অ্যাম্বিয়েন্ট গ্লো */}
      <div className="absolute inset-0 cyber-grid-bg opacity-70" />
      <div className="absolute top-1/4 left-1/4 h-[500px] w-[500px] rounded-full bg-cyan-500/[0.04] blur-[120px]" />
      <div className="absolute bottom-1/4 right-1/4 h-[500px] w-[500px] rounded-full bg-[#FF1E56]/[0.05] blur-[140px]" />

      {/* EEE SUST ডিপার্টমেন্ট লোগো হলোগ্রাফিক ওয়াটারমার্ক */}
      <div className="relative flex items-center justify-center opacity-[0.06] select-none">
        <svg
          className="w-[700px] h-[700px] max-w-[90vw] text-cyan-400 animate-[spin_180s_linear_infinite]"
          viewBox="0 0 200 200"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle cx="100" cy="100" r="90" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 4" />
          <circle cx="100" cy="100" r="82" stroke="#FF1E56" strokeWidth="0.8" />
          <circle cx="100" cy="100" r="68" stroke="currentColor" strokeWidth="2" strokeDasharray="20 10 5 10" />
          <circle cx="100" cy="100" r="54" stroke="currentColor" strokeWidth="1" strokeDasharray="8 6" />
          <path d="M 40 100 Q 70 60, 100 100 T 160 100" stroke="#00F0FF" strokeWidth="2" />
          <path d="M 40 100 Q 70 140, 100 100 T 160 100" stroke="#FF1E56" strokeWidth="2" />
          <line x1="100" y1="20" x2="100" y2="180" stroke="currentColor" strokeWidth="1" strokeDasharray="6 4" />
          <line x1="20" y1="100" x2="180" y2="100" stroke="currentColor" strokeWidth="1" strokeDasharray="6 4" />
          <circle cx="100" cy="100" r="28" fill="rgba(0,240,255,0.05)" stroke="#00F0FF" strokeWidth="2" />
          <circle cx="100" cy="100" r="8" fill="#FF1E56" />
          <text x="100" y="104" textAnchor="middle" fill="#00F0FF" fontSize="10" fontFamily="monospace" fontWeight="bold" letterSpacing="2">
            EEE • SUST
          </text>
        </svg>
        <div className="absolute w-[580px] h-[580px] rounded-full border border-dashed border-[#FF1E56]/20" />
      </div>
    </div>
  );
};