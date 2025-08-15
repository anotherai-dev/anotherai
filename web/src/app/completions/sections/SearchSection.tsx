"use client";

import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { LoadingIndicator } from "@/components/LoadingIndicator";
import { SqlKeywordExtension } from "@/components/SqlKeywordExtension";

interface Props {
  onSearch?: (query: string) => void;
  defaultValue?: string;
  placeholder?: string;
  isLoading?: boolean;
  readOnly?: boolean;
}

export function SearchSection({
  onSearch,
  defaultValue = "",
  placeholder = "Enter SQL query to search...",
  isLoading = false,
  readOnly = false,
}: Props) {
  const [searchQuery, setSearchQuery] = useState(defaultValue);

  const handleSearch = () => {
    if (onSearch) {
      onSearch(searchQuery);
    }
  };

  const editor = useEditor({
    editorProps: {
      attributes: {
        class: "focus:outline-none whitespace-pre-wrap w-full min-h-[20px] max-h-[120px] overflow-y-auto",
        autocorrect: "off",
        autocapitalize: "off",
        spellcheck: "false",
      },
      handleKeyDown: (view, event) => {
        if (event.key === "Enter" && !event.shiftKey && !isLoading) {
          event.preventDefault();
          handleSearch();
          return true;
        }
        return false;
      },
    },
    editable: !isLoading && !readOnly,
    parseOptions: {
      preserveWhitespace: "full",
    },
    extensions: [
      StarterKit.configure({
        hardBreak: {
          keepMarks: true,
        },
        paragraph: {
          HTMLAttributes: {
            class: "leading-normal",
          },
        },
      }),
      SqlKeywordExtension,
    ],
    content: defaultValue,
    onUpdate: ({ editor }) => {
      const newText = editor.getText();
      if (newText !== searchQuery) {
        setSearchQuery(newText);
      }
    },
    immediatelyRender: false,
  });

  // Update searchQuery and editor content when defaultValue changes (e.g., from URL parameters)
  useEffect(() => {
    setSearchQuery(defaultValue);
    if (editor && editor.getText() !== defaultValue) {
      editor.commands.setContent(defaultValue);
    }
  }, [defaultValue, editor]);

  return (
    <div className="flex gap-2">
      <div className="flex-1 relative">
        <div
          className={`w-full border border-gray-200 rounded-[2px] text-[13px] ${!readOnly ? "focus-within:outline-2 focus-within:outline-gray-900 focus-within:border-transparent" : ""} text-gray-900 bg-white flex items-center`}
        >
          <div className="pl-3 pr-2 flex-shrink-0">
            <Search size={14} className="text-gray-400" />
          </div>
          <div className="flex-1 py-2 pr-3">
            <EditorContent editor={editor} className="w-full" />
          </div>
        </div>
        {editor?.isEmpty && placeholder && (
          <div className="absolute top-2 left-9 text-gray-500 text-[13px] pointer-events-none">{placeholder}</div>
        )}
      </div>
      {!readOnly && (
        <button
          onClick={handleSearch}
          disabled={isLoading}
          className="text-white px-6 py-2 rounded-[2px] text-[13px] font-semibold cursor-pointer transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center"
          style={{ backgroundColor: "#3B82F6" }}
          onMouseEnter={(e) => !isLoading && (e.currentTarget.style.backgroundColor = "#2563EB")}
          onMouseLeave={(e) => !isLoading && (e.currentTarget.style.backgroundColor = "#3B82F6")}
        >
          {isLoading ? <LoadingIndicator size={16} /> : "Search"}
        </button>
      )}
    </div>
  );
}
