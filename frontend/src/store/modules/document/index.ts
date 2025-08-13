import { defineStore } from 'pinia';
import { ManualState } from './types';

const useManualStore = defineStore('manual', {
  state: (): ManualState => ({
    currentDocumentId: '',
    currentNodeId: '',
    copiedNodeId: '',
  }),

  getters: {
    manualInfo(state: ManualState): ManualState {
      return { ...state };
    },
  },

  actions: {
    setCurrentDocumentId(documentId: string) {
      this.currentDocumentId = documentId;
    },
    setCurrentNodeId(nodeId: string) {
      this.currentNodeId = nodeId;
    },
    setCopiedNodeId(nodeId: string) {
      this.copiedNodeId = nodeId;
    },
    setManualState(partial: Partial<ManualState>) {
      this.$patch(partial);
    },
  },
});

export default useManualStore;
