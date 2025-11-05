import {
  FileCode,
  Folder,
  ChevronRight,
  ChevronDown,
  ExternalLink,
} from "lucide-react";
import { useState } from "react";

interface FilesListProps {
  files: string[];
  appUrl: string | null;
}

interface FileNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children?: FileNode[];
}

function buildFileTree(files: string[]): FileNode[] {
  const root: FileNode[] = [];

  files.forEach((filePath) => {
    const parts = filePath.split("/");
    let currentLevel = root;
    let currentPath = "";

    parts.forEach((part, index) => {
      currentPath += (index === 0 ? "" : "/") + part;
      const isLastPart = index === parts.length - 1;

      let existingNode = currentLevel.find((node) => node.name === part);

      if (!existingNode) {
        existingNode = {
          name: part,
          path: currentPath,
          isDirectory: !isLastPart,
          children: !isLastPart ? [] : undefined,
        };
        currentLevel.push(existingNode);
      }

      if (!isLastPart && existingNode.children) {
        currentLevel = existingNode.children;
      }
    });
  });

  return root;
}

function getFileExtension(filename: string): string {
  const parts = filename.split(".");
  return parts.length > 1 ? parts[parts.length - 1] : "";
}

function getFileIcon(filename: string) {
  const ext = getFileExtension(filename);
  const colorMap: Record<string, string> = {
    tsx: "text-blue-400",
    ts: "text-blue-400",
    jsx: "text-cyan-400",
    js: "text-yellow-400",
    css: "text-pink-400",
    json: "text-green-400",
    html: "text-orange-400",
    md: "text-gray-400",
  };

  return <FileCode className={`w-4 h-4 ${colorMap[ext] || "text-white/60"}`} />;
}

function FileTreeNode({
  node,
  appUrl,
  depth = 0,
}: {
  node: FileNode;
  appUrl: string | null;
  depth?: number;
}) {
  const [isExpanded, setIsExpanded] = useState(depth === 0);

  const handleFileClick = () => {
    if (!node.isDirectory && appUrl) {
      // Open file in new tab by constructing URL to the file
      const fileUrl = `${appUrl}/${node.path}`;
      window.open(fileUrl, "_blank");
    }
  };

  return (
    <div>
      <div
        className={`flex items-center gap-2 py-1.5 px-2 rounded hover:bg-white/5 cursor-pointer transition-colors ${
          !node.isDirectory ? "hover:bg-white/10" : ""
        }`}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => {
          if (node.isDirectory) {
            setIsExpanded(!isExpanded);
          } else {
            handleFileClick();
          }
        }}
      >
        {node.isDirectory ? (
          <>
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-white/40" />
            ) : (
              <ChevronRight className="w-4 h-4 text-white/40" />
            )}
            <Folder className="w-4 h-4 text-yellow-400/80" />
            <span className="text-sm text-white/80 font-medium">
              {node.name}
            </span>
          </>
        ) : (
          <>
            <div className="w-4" />
            {getFileIcon(node.name)}
            <span className="text-sm text-white/70 flex-1">{node.name}</span>
            <ExternalLink className="w-3 h-3 text-white/30 opacity-0 group-hover:opacity-100" />
          </>
        )}
      </div>

      {node.isDirectory && isExpanded && node.children && (
        <div>
          {node.children.map((child) => (
            <FileTreeNode
              key={child.path}
              node={child}
              appUrl={appUrl}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FilesList({ files, appUrl }: FilesListProps) {
  const fileTree = buildFileTree(files);

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-white/40">
        <FileCode className="w-12 h-12 mb-4" />
        <p className="text-sm">No files available yet</p>
        <p className="text-xs mt-1">Files will appear once your app is built</p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="mb-4 pb-3 border-b border-white/10">
        <h3 className="text-white/90 font-semibold text-sm">Project Files</h3>
        <p className="text-white/50 text-xs mt-1">
          {files.length} file{files.length !== 1 ? "s" : ""} • Click to open in
          new tab
        </p>
      </div>

      <div className="space-y-0.5">
        {fileTree.map((node) => (
          <FileTreeNode key={node.path} node={node} appUrl={appUrl} />
        ))}
      </div>
    </div>
  );
}
