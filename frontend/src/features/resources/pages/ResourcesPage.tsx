import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, FileText } from 'lucide-react';

export default function ResourcesPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Resource Hub</h1>
      <Card>
        <CardContent className="p-5 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <FileText className="h-6 w-6 text-emerald-600" />
            <div>
              <p className="font-bold text-sm">EEE 311: Chapter 4 Armature Reaction</p>
              <p className="text-xs text-slate-400">PDF • 3.4 MB • Verified by Dr. Tasfiq</p>
            </div>
          </div>
          <Button size="sm"><Download className="h-4 w-4 mr-1" /> Download</Button>
        </CardContent>
      </Card>
    </div>
  );
}
