import axios from 'axios';

// eslint-disable-next-line no-shadow
export enum DocumentStatus {
  pending = 'pending',
  processing = 'processing',
  completed = 'completed',
  failed = 'failed',
}

export interface OcrResult {
  id: string | null;
  documentId: string | null;
  engine: string | null;
  extractedText: string | null;
  textPreview: string | null;
  confidenceScore: number | null;
  processingTimeMs: number | null;
  estimatedCost: number | null;
  processedAt: string | null;
  errorMessage: string | null;
}

export interface Document {
  id: string | null;
  filename: string | null;
  fileType: string | null;
  filePath: string | null;
  fileSize: number | null;
  uploadTimestamp: string | null;
  status: string | null;
  searchableContent: string | null;
  recommendation: string | null;
  createdAt: string | null;
  updatedAt: string | null;
  ocrResults: OcrResult[] | null;
  ocrProgress: number | 0;
}

export interface DocumentView {
  id: string | null;
  filename: string | null;
  fileType: string | null;
  filePath: string | null;
  fileSize: number | null;
  uploadTimestamp: string | null;
  status: string | null;
  searchableContent: string | null;
}

export interface DocumentList {
  searchKeywords: string | null;
  status: string | null;
  fromTime?: string | null;
  toTime?: string | null;
  sortBy?: string | null;
  desc?: boolean | null;
  current?: number | null;
  pageSize?: number | null;
}

export interface DocumentFindResult {
  total: number;
  documents: Document[];
}

export interface ParseResult {
  document_id: string;
  message: string;
  websocketUrl: string;
}
export const getUploadUrl = () => {
  return `${axios.defaults.baseURL}/api/documents/upload`;
};

export const getDownloadUrl = (filePath: string) => {
  return `${axios.defaults.baseURL}/download?storage_path=${filePath}`;
};

export const getPreviewUrl = (filePath: string) => {
  return `${axios.defaults.baseURL}/preview?storage_path=${filePath}`;
};

export function saveDocument(data: DocumentView) {
  return axios.put<Document>(`/api/documents`, data);
}

export function deleteDocument(id: string) {
  return axios.delete<Document>(`/api/documents/${id}`);
}

export function findDocumentById(id: string) {
  return axios.get<Document>(`/api/documents/find/${id}`);
}

export function findDocumentByCondition(data: DocumentList) {
  return axios.post<DocumentFindResult>(`/api/documents`, data);
}

export function parseDocument(id: string) {
  return axios.post<ParseResult>(`/api/documents/parse/${id}`);
}

export function exportParseResult(id: string) {
  return axios.post<string>(`/api/documents/download_parse_result/${id}`);
}
