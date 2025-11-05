import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface FormattedMessageProps {
  content: string;
  formatted?: string;
  type?: string;
}

export function FormattedMessage({
  content,
  formatted,
  type,
}: FormattedMessageProps) {
  // Use formatted content if available, otherwise use raw content
  const displayContent = formatted || content;

  // Check if content is likely JSON (unformatted)
  const isJson =
    !formatted &&
    (content.trim().startsWith("{") || content.trim().startsWith("["));

  if (isJson) {
    try {
      const parsed = JSON.parse(content);
      return (
        <details className="my-2 bg-white/5 rounded-lg border border-white/10">
          <summary className="cursor-pointer px-4 py-2 font-medium text-white/70 hover:text-white">
            View Raw Data
          </summary>
          <pre className="px-4 pb-4 text-xs text-white/60 overflow-x-auto">
            {JSON.stringify(parsed, null, 2)}
          </pre>
        </details>
      );
    } catch {
      // If parsing fails, render as plain text
    }
  }

  return (
    <div className="formatted-message prose prose-invert max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || "");
            const language = match ? match[1] : "";

            return !inline ? (
              <div className="relative group">
                <SyntaxHighlighter
                  style={vscDarkPlus as any}
                  language={language || "text"}
                  PreTag="div"
                  className="rounded-md text-sm"
                  {...props}
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(String(children));
                  }}
                  className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity px-2 py-1 bg-white/10 hover:bg-white/20 rounded text-xs text-white"
                >
                  Copy
                </button>
              </div>
            ) : (
              <code
                className="bg-white/10 px-1 py-0.5 rounded text-sm"
                {...props}
              >
                {children}
              </code>
            );
          },
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold text-white mt-6 mb-4">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-semibold text-white mt-5 mb-3">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-medium text-white/90 mt-4 mb-2">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-base font-medium text-white/80 mt-3 mb-2">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="text-white/70 leading-relaxed my-2">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-1 text-white/70 my-2">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-1 text-white/70 my-2">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-white/70 ml-2">{children}</li>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white/90">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-white/80">{children}</em>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-blue-500/50 pl-4 py-2 my-3 text-white/60 italic">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full border-collapse border border-white/20">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-white/20 px-4 py-2 bg-white/5 text-left font-semibold text-white">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-white/20 px-4 py-2 text-white/70">
              {children}
            </td>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 underline"
            >
              {children}
            </a>
          ),
        }}
      >
        {displayContent}
      </ReactMarkdown>

      <style jsx global>{`
        .formatted-message {
          line-height: 1.6;
        }
        .formatted-message > *:first-child {
          margin-top: 0;
        }
        .formatted-message > *:last-child {
          margin-bottom: 0;
        }
      `}</style>
    </div>
  );
}
