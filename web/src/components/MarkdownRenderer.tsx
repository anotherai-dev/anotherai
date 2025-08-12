import { cx } from "class-variance-authority";
import ReactMarkdown from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export default function MarkdownRenderer({
  content,
  className = "",
}: MarkdownRendererProps) {
  return (
    <div
      className={cx(
        "flex flex-col w-full prose prose-sm max-w-none",
        "[&>ul]:list-disc [&>ul]:pl-6 [&>ul]:space-y-4 [&>ul]:my-4",
        "prose-a:text-blue-600 prose-a:underline hover:prose-a:text-blue-800",
        "prose-h1:text-base prose-h1:font-semibold prose-h1:mb-2",
        "prose-h2:text-sm prose-h2:font-semibold prose-h2:mb-2",
        "prose-h3:text-xs prose-h3:font-semibold prose-h3:mb-2",
        "[&>table]:border-collapse [&>table]:w-full",
        "[&>table_th]:border [&>table_th]:border-gray-300 [&>table_th]:p-2 [&>table_th]:bg-gray-50",
        "[&>table_td]:border [&>table_td]:border-gray-300 [&>table_td]:p-2",
        "[&>details]:border [&>details]:border-gray-200 [&>details]:rounded-md [&>details]:p-2",
        "[&>details_summary]:cursor-pointer [&>details_summary]:font-medium",
        "[&_kbd]:bg-gray-100 [&_kbd]:border [&_kbd]:border-gray-300 [&_kbd]:rounded [&_kbd]:px-1.5 [&_kbd]:py-0.5 [&_kbd]:text-xs [&_kbd]:font-semibold",
        "[&_code]:text-[12px]",
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold mb-4">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-semibold mb-3">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-medium mb-2">{children}</h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-base font-medium mb-2">{children}</h4>
          ),
          h5: ({ children }) => (
            <h5 className="text-sm font-medium mb-1">{children}</h5>
          ),
          h6: ({ children }) => (
            <h6 className="text-xs font-medium mb-1">{children}</h6>
          ),
          strong: ({ children }) => (
            <strong className="font-bold">{children}</strong>
          ),
          em: ({ children }) => <em className="italic">{children}</em>,
          code: ({ children }) => (
            <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto font-mono text-sm mb-4">
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-gray-400 pl-4 italic my-4">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <table className="w-full border-collapse border border-gray-300 my-4">
              {children}
            </table>
          ),
          th: ({ children }) => (
            <th className="border border-gray-300 bg-gray-100 px-4 py-2 text-left font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-gray-300 px-4 py-2">{children}</td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
