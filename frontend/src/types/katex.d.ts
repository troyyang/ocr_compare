declare module 'katex' {
  export interface KatexOptions {
    throwOnError?: boolean;
    output?: 'html' | 'mathml';
    [key: string]: any;
  }

  export function renderToString(latex: string, options?: KatexOptions): string;
  export function render(latex: string, element: HTMLElement, options?: KatexOptions): void;
  
  const katex: {
    renderToString: typeof renderToString;
    render: typeof render;
  };
  
  export default katex;
} 