import { Eye, FileCode, Globe, ExternalLink } from "lucide-react";
import { useState } from "react";
import { FileViewer } from "./FileViewer";

interface PreviewPanelProps {
  appUrl: string | null;
  isCheckingUrl: boolean;
  previewWidth: number;
  files: string[];
  projectId: string;
}

type TabType = 'preview' | 'files';

export function PreviewPanel({ appUrl, isCheckingUrl, previewWidth, files, projectId }: PreviewPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('preview');

  return (
    <div 
      className="flex flex-col bg-black/50 border-l border-white/5"
      style={{
        width: `${previewWidth}%`,
      }}
    >
      {/* Tabs Header */}
      <div className="flex items-center justify-between border-b border-white/5 bg-black/30">
        <div className="flex">
          <button
            onClick={() => setActiveTab('preview')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === 'preview'
                ? 'text-white border-b-2 border-white bg-white/5'
                : 'text-white/50 hover:text-white/80 hover:bg-white/5'
            }`}
          >
            <Globe className="w-3.5 h-3.5" />
            Preview
          </button>
          <button
            onClick={() => setActiveTab('files')}
            className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === 'files'
                ? 'text-white border-b-2 border-white bg-white/5'
                : 'text-white/50 hover:text-white/80 hover:bg-white/5'
            }`}
          >
            <FileCode className="w-3.5 h-3.5" />
            Files {files.length > 0 && `(${files.length})`}
          </button>
        </div>
        
        {/* Open in New Tab button - only shows when URL is available */}
        {appUrl && !isCheckingUrl && (
          <button
            onClick={() => window.open(appUrl, '_blank')}
            className="flex items-center gap-1.5 px-3 py-2 mx-2 text-xs font-medium text-white/70 hover:text-white hover:bg-white/10 rounded transition-colors"
            title="Open in new tab"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Open
          </button>
        )}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'preview' ? (
          <div className="h-full p-6">
            {isCheckingUrl ? (
              <div className="w-full h-full rounded-lg border border-white/10 flex items-center justify-center">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white/60 mx-auto mb-4" />
                  <p className="text-white/60 font-sans">Checking if app is ready...</p>
                </div>
              </div>
            ) : appUrl ? (
              <div className="w-full h-full rounded-lg overflow-hidden border border-white/10">
                <iframe
                  src={appUrl}
                  title="App Preview"
                  className="w-full h-full"
                  sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
                />
              </div>
            ) : (
              <div className="w-full h-full rounded-lg border border-white/10 flex items-center justify-center">
                <div className="text-center">
                  <Eye className="w-12 h-12 text-white/20 mx-auto mb-4" />
                  <p className="text-white/60 font-sans">Preview will appear here</p>
                </div>
              </div>
            )}
          </div>
        ) : (
          <FileViewer files={files} projectId={projectId} />
        )}
      </div>
    </div>
  );
}
