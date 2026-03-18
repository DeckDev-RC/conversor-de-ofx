/// <reference types="vite/client" />

declare module '*.png' {
  const value: string;
  export default value;
}
declare module '*.jpg' {
  const value: string;
  export default value;
}
declare module '*.svg' {
  import React = require('react');
  export const ReactComponent: React.FC<React.SVGProps<SVGSVGElement>>;
  const src: string;
  export default src;
}

interface Window {
  electronAPI: {
    getPathForFile: (file: File) => string;
    parseFiles: (filePaths: string[]) => Promise<any>;
    selectFiles: () => Promise<string[]>;
    exportJSON: (data: object, defaultName: string) => Promise<void>;
    exportOFX: (filePaths: string[]) => Promise<void>;
    onBackendStatus: (callback: (status: string) => void) => void;
    windowMinimize: () => void;
    windowMaximize: () => void;
    windowClose: () => void;
    windowIsMaximized: () => Promise<boolean>;
    onWindowMaximized: (callback: (isMaximized: boolean) => void) => void;
  }
}
