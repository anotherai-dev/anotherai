import type { MDXComponents } from "mdx/types";

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    h1: ({ children }) => <h1 className="text-4xl font-normal text-gray-900 mb-6">{children}</h1>,
    h2: ({ children }) => <h2 className="text-3xl font-normal text-gray-900 mt-12 mb-6">{children}</h2>,
    h3: ({ children }) => <h3 className="text-2xl font-normal text-gray-900 mt-8 mb-4">{children}</h3>,
    p: ({ children }) => <p className="text-lg text-gray-600 leading-relaxed mb-6">{children}</p>,
    ul: ({ children }) => <ul className="space-y-2 text-gray-600 mb-6">{children}</ul>,
    li: ({ children }) => <li>– {children}</li>,
    a: ({ href, children }) => (
      <a href={href} className="text-blue-600 hover:underline">
        {children}
      </a>
    ),
    strong: ({ children }) => <strong className="font-medium">{children}</strong>,
    code: ({ children }) => (
      <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono text-gray-800">{children}</code>
    ),
    pre: ({ children }) => (
      <div className="bg-gray-100 border border-gray-200 rounded p-4 mb-6">
        <pre className="text-sm font-mono text-gray-800 whitespace-pre-wrap">{children}</pre>
      </div>
    ),
    // Handle MDX content blocks like [video] and [screenshot]
    div: ({ children }) => {
      // If it's a text node with [video] or [screenshot], render as placeholder
      if (typeof children === "string" && (children === "[video]" || children === "[screenshot]")) {
        return <div className="bg-gray-900 text-white p-4 rounded text-center mb-6">{children}</div>;
      }
      return <div>{children}</div>;
    },
    ...components,
  };
}
