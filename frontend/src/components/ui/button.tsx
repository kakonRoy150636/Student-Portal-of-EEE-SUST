import * as React from "react"
import { cn } from "@/lib/utils"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "outline" | "ghost" | "secondary" | "destructive";
  size?: "default" | "sm" | "lg" | "icon";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50",
        variant === "default" && "bg-emerald-600 text-white hover:bg-emerald-700",
        variant === "outline" && "border border-slate-200 bg-transparent hover:bg-slate-100 dark:border-slate-800 dark:hover:bg-slate-800",
        variant === "ghost" && "hover:bg-slate-100 dark:hover:bg-slate-800",
        variant === "destructive" && "bg-rose-600 text-white hover:bg-rose-700",
        size === "default" && "h-9 px-4 py-2",
        size === "sm" && "h-8 rounded-md px-3 text-xs",
        size === "icon" && "h-9 w-9",
        className
      )}
      {...props}
    />
  )
)
Button.displayName = "Button"
