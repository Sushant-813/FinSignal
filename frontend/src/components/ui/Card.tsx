import type { HTMLAttributes } from "react";
import { cn } from "../../lib/utils/cn.ts";

export type CardPadding = "none" | "sm" | "md" | "lg";

export interface CardProps extends HTMLAttributes<HTMLElement> {
  padding?: CardPadding | undefined;
  elevated?: boolean | undefined;
  as?: "div" | "section" | "article" | undefined;
}

const paddingClasses: Record<CardPadding, string> = {
  none: "p-0",
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
};

export function Card({
  padding = "md",
  elevated = false,
  as: Component = "div",
  className,
  ...props
}: CardProps) {
  return (
    <Component
      className={cn(
        "rounded-panel border border-border bg-surface text-text-primary",
        elevated && "shadow-card",
        paddingClasses[padding],
        className
      )}
      {...props}
    />
  );
}

export type CardHeaderProps = HTMLAttributes<HTMLDivElement>;

export function CardHeader({ className, ...props }: CardHeaderProps) {
  return <div className={cn("flex flex-col gap-1 pb-4", className)} {...props} />;
}

export type CardTitleSize = "panel" | "section" | "page";

export interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  as?: "h1" | "h2" | "h3" | "h4" | undefined;
  size?: CardTitleSize | undefined;
}

const titleSizeClasses: Record<CardTitleSize, string> = {
  panel: "text-[15px] leading-[22px]",
  section: "text-[18px] leading-[26px]",
  page: "text-[24px] leading-[32px]",
};

export function CardTitle({
  as: Heading = "h2",
  size = "panel",
  className,
  ...props
}: CardTitleProps) {
  return (
    <Heading
      className={cn(titleSizeClasses[size], "font-semibold text-text-primary", className)}
      {...props}
    />
  );
}

export type CardDescriptionProps = HTMLAttributes<HTMLParagraphElement>;

export function CardDescription({ className, ...props }: CardDescriptionProps) {
  return (
    <p className={cn("text-[13px] leading-[19px] text-text-secondary", className)} {...props} />
  );
}

export type CardContentProps = HTMLAttributes<HTMLDivElement>;

export function CardContent({ className, ...props }: CardContentProps) {
  return <div className={cn("text-sm text-text-primary", className)} {...props} />;
}

export type CardFooterProps = HTMLAttributes<HTMLDivElement>;

export function CardFooter({ className, ...props }: CardFooterProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-end gap-2 pt-4 border-t border-border mt-4",
        className
      )}
      {...props}
    />
  );
}
