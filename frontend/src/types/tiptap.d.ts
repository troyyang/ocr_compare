import { Editor } from '@tiptap/vue-3';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    attachment: {
      /**
       * Insert an attachment
       */
      insertAttachment: (options: { 
        url: string; 
        fileName: string;
      }) => ReturnType;
    };
  }
}
