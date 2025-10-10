import { compileMDX } from "next-mdx-remote/rsc";
import Image from "next/image";
import { ReactElement } from "react";
import remarkGfm from "remark-gfm";
import { CopyButton } from "./CopyButton";
import { bundledPreviewContent } from "./bundled-content";

export interface PreviewContentData {
  content: ReactElement;
  title: string;
}

export async function getPreviewContent(): Promise<PreviewContentData | null> {
  try {
    const { content } = await compileMDX({
      source: bundledPreviewContent.content,
      options: {
        parseFrontmatter: false,
        mdxOptions: {
          remarkPlugins: [remarkGfm],
        },
      },
      components: {
        p: ({ children }) => {
          if (typeof children === "string" && children === "[screenshot]") {
            return (
              <div className="mb-6">
                <Image
                  src="https://workflowai.blob.core.windows.net/workflowai-public/anotherai/experiment.png"
                  alt="AnotherAI experiment interface"
                  width={800}
                  height={600}
                  className="w-full h-auto rounded-[2px] border border-gray-200 shadow-sm"
                />
              </div>
            );
          }
          if (typeof children === "string" && children === "[video]") {
            return null;
          }
          return <p className="text-base text-gray-600 leading-relaxed mb-4">{children}</p>;
        },
        h2: ({ children }) => {
          // Create an ID from the text content
          const text =
            typeof children === "string" ? children : Array.isArray(children) ? children.join("") : "section";
          const id = text
            .toLowerCase()
            .replace(/[^\w\s-]/g, "") // Remove special chars
            .replace(/\s+/g, "-") // Replace spaces with hyphens
            .replace(/-+/g, "-"); // Remove multiple hyphens

          // Map specific sections to the header link IDs
          const sectionMap: { [key: string]: string } = {
            "ai-that-can-compare-models-performance-price-and-latency": "compare-models",
            "ai-learns-from-production-data": "ai-learns",
            "ai-learns-from-users-feedback": "ai-learns",
            "try-it": "try-it",
          };

          const finalId = sectionMap[id] || id;

          return (
            <h2 id={finalId} className="text-2xl font-normal text-gray-900 mt-10 mb-4 scroll-mt-24">
              {children}
            </h2>
          );
        },
        h3: ({ children }) => <h3 className="text-xl font-normal text-gray-900 mt-6 mb-3">{children}</h3>,
        ul: ({ children }) => <ul className="space-y-1 text-gray-600 mb-4 text-base list-disc pl-6">{children}</ul>,
        li: ({ children }) => <li>{children}</li>,
        a: ({ href, children }) => {
          // Check if the link is external (starts with http/https or is absolute)
          const isExternal =
            href && (href.startsWith("http://") || href.startsWith("https://") || href.startsWith("//"));

          return (
            <a
              href={href}
              className="text-blue-600 hover:underline"
              {...(isExternal && {
                target: "_blank",
                rel: "noopener noreferrer",
              })}
            >
              {children}
            </a>
          );
        },
        strong: ({ children }) => <strong className="font-medium">{children}</strong>,
        code: ({ children }) => (
          <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono text-gray-800">{children}</code>
        ),
        pre: ({ children }) => {
          // Extract text content from children for copying
          const getText = (content: unknown): string => {
            if (typeof content === "string") {
              return content;
            }
            if (Array.isArray(content)) {
              return content.map(getText).join("");
            }
            if (content && typeof content === "object" && "props" in content) {
              const props = (content as { props?: { children?: unknown } }).props;
              if (props?.children) {
                return getText(props.children);
              }
            }
            return "";
          };

          const textToCopy = getText(children);

          return (
            <div className="bg-gray-100 border border-gray-200 rounded mb-6 relative group">
              <CopyButton text={textToCopy} />
              <div className="p-4">
                <pre className="text-sm font-mono text-gray-800 whitespace-pre-wrap">{children}</pre>
              </div>
            </div>
          );
        },
        // Handle special content blocks like [video] and [screenshot]
        div: ({ children }) => {
          if (typeof children === "string" && children === "[video]") {
            return null;
          }
          if (typeof children === "string" && children === "[screenshot]") {
            return (
              <div className="mb-6">
                <Image
                  src="https://workflowai.blob.core.windows.net/workflowai-public/anotherai/experiment.png"
                  alt="AnotherAI experiment interface"
                  width={800}
                  height={600}
                  className="w-full h-auto rounded-[2px] border border-gray-200 shadow-sm"
                />
              </div>
            );
          }
          return <div>{children}</div>;
        },
        // Simple Accordion components
        Accordions: ({ children }) => <div className="space-y-4 mt-8">{children}</div>,
        Accordion: ({ title, children }: { title: string; children: React.ReactNode }) => (
          <details className="border border-gray-200 rounded-lg overflow-hidden">
            <summary className="px-4 py-3 font-medium cursor-pointer hover:bg-gray-100 text-gray-900">{title}</summary>
            <div className="px-4 pb-4 pt-2 text-gray-600 text-base border-t border-gray-100">{children}</div>
          </details>
        ),
      },
    });

    return {
      content,
      title: bundledPreviewContent.frontmatter.title || "AnotherAI Preview",
    };
  } catch (error) {
    console.error("Failed to load preview content:", error);
    return null;
  }
}
