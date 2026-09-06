import * as React from "react"
import { cn } from "@/lib/utils"

export const Badge = ({ className, variant = "default", ...props }: React.HTMLAttributes<HTMLDivElement> & { variant?: "default" | "secondary" | "outline" }) => (
  <div className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold", 
    variant === "default" && "border-transparent bg-emerald-600 text-white",
    variant === "secondary" && "border-transparent bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-50",
    variant === "outline" && "text-slate-950 dark:text-slate-50",
    className
  )} {...props} />
)
