import * as React from "react"

export const Dialog = ({ children, open }: { children: React.ReactNode; open?: boolean; onOpenChange?: (open: boolean) => void }) => <div>{children}</div>
export const DialogTrigger = ({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) => <div>{children}</div>
export const DialogContent = ({ children }: { children: React.ReactNode; className?: string }) => <div className="p-4 bg-white dark:bg-slate-900 rounded-lg shadow-lg border">{children}</div>
export const DialogHeader = ({ children }: { children: React.ReactNode }) => <div className="mb-4">{children}</div>
export const DialogTitle = ({ children }: { children: React.ReactNode }) => <h2 className="text-lg font-bold">{children}</h2>
