import React from 'react';
import { useLocation } from 'react-router-dom';

export const Breadcrumbs = () => {
  const location = useLocation();
  const path = location.pathname.replace('/', '').toUpperCase();
  return <div className="text-xs text-slate-400 pb-2">SUST EEE / {path || 'DASHBOARD'}</div>;
};
