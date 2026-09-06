import * as React from "react"

export const Select = ({ children }: any) => <div className="relative">{children}</div>
export const SelectTrigger = ({ children }: any) => <button type="button" className="flex h-9 w-full items-center justify-between border rounded-md px-3 text-sm">{children}</button>
export const SelectValue = ({ placeholder }: any) => <span>{placeholder}</span>
export const SelectContent = ({ children }: any) => <div className="mt-1 border rounded-md p-1 bg-white dark:bg-slate-900">{children}</div>
export const SelectItem = ({ value, children }: any) => <div className="p-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer">{children}</div>
