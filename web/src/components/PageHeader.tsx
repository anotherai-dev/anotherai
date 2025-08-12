import { Copy } from "lucide-react";
import Link from "next/link";
import { useToast } from "./ToastProvider";

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  breadcrumbs: BreadcrumbItem[];
  title: string;
  description?: string;
  copyablePrefixAndId?: string;
  className?: string;
  rightContent?: React.ReactNode;
}

export function PageHeader(props: PageHeaderProps) {
  const {
    breadcrumbs,
    title,
    description,
    copyablePrefixAndId,
    className = "mb-8",
    rightContent,
  } = props;
  const { showToast } = useToast();

  const handleCopy = async () => {
    if (copyablePrefixAndId) {
      try {
        await navigator.clipboard.writeText(copyablePrefixAndId);
        showToast("Copied to clipboard");
      } catch (err) {
        console.error("Failed to copy: ", err);
        showToast("Failed to copy");
      }
    }
  };

  return (
    <div className={className}>
      <div className="flex items-center gap-2 text-xs text-gray-600 mb-4">
        {breadcrumbs.map((breadcrumb, index) => (
          <div key={index} className="flex items-center gap-2">
            {index > 0 && <span>→</span>}
            {breadcrumb.href ? (
              <Link href={breadcrumb.href} className="hover:text-gray-900">
                {breadcrumb.label}
              </Link>
            ) : (
              <span className="text-gray-900">{breadcrumb.label}</span>
            )}
          </div>
        ))}
      </div>

      <h1 className="text-2xl font-semibold text-gray-900 mb-2">{title}</h1>

      {copyablePrefixAndId && (
        <div className="flex items-center justify-between gap-1 mb-3">
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-700 font-mono bg-white px-2 py-1 rounded-[2px] border border-gray-200">
              {copyablePrefixAndId}
            </span>
            <button
              onClick={handleCopy}
              className="p-1 text-gray-700 bg-white border border-gray-200 rounded-[2px] cursor-pointer hover:text-gray-600 hover:bg-gray-100 transition-colors"
              title="Copy to clipboard"
            >
              <Copy size={14} />
            </button>
          </div>
          {rightContent && <div className="flex-shrink-0">{rightContent}</div>}
        </div>
      )}

      {description && <p className="text-sm text-gray-600">{description}</p>}
    </div>
  );
}
