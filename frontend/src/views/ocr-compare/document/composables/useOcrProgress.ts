// composables/useOcrProgress.ts
import { ref, onUnmounted, Ref } from 'vue';
import { Message } from '@arco-design/web-vue';
import axios from 'axios';
import { getToken } from '@/utils/auth';

export interface ProgressData {
  document_id: string;
  stage: string;
  current: number;
  total: number;
  percentage: number;
  message: string;
  completed?: boolean;
  success?: boolean;
  timestamp: number;
}

export function useOcrProgress(onProgress: (progress: ProgressData) => void) {
  const isConnected = ref(false);
  const progress = ref<ProgressData | null>(null);
  const error = ref<string | null>(null);

  const baseUrl = axios.defaults.baseURL || window.location.origin;
  const url = new URL(baseUrl);
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${wsProtocol}//${url.host}/app_ws`;
  const websocket: Ref<WebSocket | null> = ref(null);
  const connect = () => {
    websocket.value = new WebSocket(wsUrl);
    websocket.value.onopen = () => {
      isConnected.value = true;
      
      // Send initial ping to confirm connection
      if (websocket.value?.readyState === WebSocket.OPEN) {
        // websocket.send(documentId);
        console.log(`WebSocket connected for OCR progress`);
      }
    };
    websocket.value.onmessage = (event) => {
      try {
        console.log(`WebSocket received message: ${event.data}`);
        const data: ProgressData = JSON.parse(event.data);
        progress.value = data;
        onProgress(data);
        // Handle completion
        if (data.completed) {
          if (data.success) {
            Message.success(data.message || 'OCR processing completed successfully');
          } else {
            Message.error(data.message || 'OCR processing failed');
          }
        }
      } catch (err) {
        console.error('Error parsing progress data:', err);
      }
    };
    
    websocket.value.onclose = (event) => {
      isConnected.value = false;
      console.log('WebSocket disconnected:', event.code, event.reason);
    };
    
    websocket.value.onerror = (event) => {
      // error.value = 'WebSocket connection error';
      console.error('WebSocket error:', event);
    };
  }

  const disconnect = () => {
    if (websocket.value) {
      websocket.value.close(1000, 'Manual disconnect');
    }
    
    isConnected.value = false;
    progress.value = null;
    error.value = null;
  };

  const sendOCRProgress = (documentId: string) => {
    if (!isConnected.value) {
      connect();
    }
    error.value = null;
    try {
      console.log(`Sending document ID: ${documentId}`);
      if (websocket.value?.readyState === WebSocket.OPEN) {
        console.log(`WebSocket readyState: ${websocket.value.readyState}`);
        websocket.value.send(JSON.stringify({doc_id: documentId, token: getToken()}));
      }
    } catch (err) {
      error.value = 'Failed to create WebSocket connection';
      console.error('Error creating WebSocket:', err);

    }
  };


  // Cleanup on unmount
  onUnmounted(() => {
    disconnect();
  });

  return {
    isConnected,
    progress,
    error,
    connect,
    disconnect,
    sendOCRProgress,
  };
}