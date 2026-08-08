// UI Renderer - renders MCP App UI templates

import React from 'react';
import type { UITemplate, UISection } from '@/types/mcp';
import { Header } from './Header';
import { StatsGrid } from './StatsGrid';
import { KnowledgeList } from './KnowledgeList';
import { Chart } from './Chart';

interface UIRendererProps {
  template: UITemplate;
}

export const UIRenderer: React.FC<UIRendererProps> = ({ template }) => {
  // If template has HTML path, render in iframe (for complex UIs like knowledge graph)
  if (template.templatePath) {
    return <HTMLRenderer template={template} />;
  }

  // Otherwise render JSON components
  return <JSONRenderer template={template} />;
};

// JSON Component Renderer
const JSONRenderer: React.FC<{ template: UITemplate }> = ({ template }) => {
  const sections = template.data.sections as UISection[] || [];

  return (
    <div className="ui-template p-4 space-y-6">
      {sections.map((section, index) => (
        <SectionRenderer key={index} section={section} />
      ))}
    </div>
  );
};

const SectionRenderer: React.FC<{ section: UISection }> = ({ section }) => {
  switch (section.type) {
    case 'header':
      return <Header title={(section as any).title || ''} />;
    case 'stats-grid':
      return <StatsGrid items={(section as any).items || []} />;
    case 'knowledge-list':
      return <KnowledgeList items={(section as any).items || []} />;
    case 'chart':
      return <Chart chartType={(section as any).chartType || 'bar'} data={(section as any).data || {}} />;
    default:
      console.warn(`Unknown section type: ${section.type}`);
      return null;
  }
};

// HTML Template Renderer (for complex UIs)
const HTMLRenderer: React.FC<{ template: UITemplate }> = ({ template }) => {
  const iframeRef = React.useRef<HTMLIFrameElement>(null);

  React.useEffect(() => {
    if (iframeRef.current) {
      const iframe = iframeRef.current;

      iframe.onload = () => {
        if (iframe.contentWindow) {
          // Inject data
          (iframe.contentWindow as any).__MCP_DATA__ = template.data;

          // Inject tool call function
          (iframe.contentWindow as any).__MCP_CALL_TOOL__ = async (
            toolName: string,
            params: Record<string, any>
          ) => {
            console.log('[HTMLRenderer] Tool call:', toolName, params);
            // TODO: integrate with mcpClient
          };
        }
      };

      // Load HTML template
      iframe.srcdoc = `
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="UTF-8">
          <title>${template.templateId}</title>
          <style>
            body { margin: 0; padding: 0; overflow: hidden; }
          </style>
        </head>
        <body>
          <div id="root">Loading...</div>
          <script>
            console.log('MCP App loaded:', window.__MCP_DATA__);
          </script>
        </body>
        </html>
      `;
    }
  }, [template]);

  return (
    <div className="html-renderer w-full h-full">
      <iframe
        ref={iframeRef}
        sandbox="allow-scripts"
        className="w-full h-full border-0"
        style={{ minHeight: '600px' }}
      />
    </div>
  );
};
