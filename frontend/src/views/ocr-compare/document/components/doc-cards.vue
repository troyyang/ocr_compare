<template>
  <DocumentSearchForm 
    form-type="list"
    @search="handleSearch" 
    @reset="handleReset"
  />
  <a-row justify="space-between" align="center" style="margin-bottom: 16px">
    <a-col :span="12">
      <a-space>
        <a-upload
          :action="getUploadUrl()"
          :file-list="docFile ? [docFile] : []"
          :show-file-list="false"
          accept=".pdf,.png,.jpg,.jpeg"
          :limit="1"
          :headers="{
            'Authorization': 'Bearer ' + token,
            'accept-language': locale,
          }"
          @change="onDocChange"
          @error="onDocError"
        >
          <a-button type="primary">
            <template #icon>
              <icon-plus />
            </template>
            {{ $t('document.operation.create') }}
          </a-button>
        </a-upload>
      </a-space>
    </a-col>
  </a-row>

  <!-- Optimized List -->
  <a-row :gutter="16">
    <a-col
      v-for="(item, index) in renderData"
      :key="index"
      :xs="24"
      :sm="12"
      :md="12"
      :lg="8"
      :xl="6"
      style="margin-bottom: 16px"
    >
    <a-card class="document-card" :class="{ 'processing': isProcessing(item) }">
        <div class="card-content">
          <a-typography-title :heading="6" :ellipsis="{ rows: 1 }">
            {{ item.filename }}
          </a-typography-title>
          
          <div class="document-meta">
            <a-space size="small" wrap>
              <a-tag color="arcoblue" size="small">{{ formatFileSize(item.fileSize) }}</a-tag>
              <a-tag color="green" size="small">{{ item.fileType }}</a-tag>
              <a-tag :color="getStatusColor(item.status || '')" size="small">
                <icon-loading v-if="isProcessing(item)" spin style="margin-right: 4px" />
                {{ $t(`document.status.${item.status}`) }}
              </a-tag>
            </a-space>

            <div class="meta-item">
              <icon-clock-circle />
              <span>{{ $t('document.createdTime') }}:</span>
              <span class="meta-value">{{ formatDate(item.createdAt) }}</span>
            </div>
          </div>

          <a-typography-paragraph 
            type="secondary"
            :ellipsis="{ rows: 3 }"
            class="document-abstract"
          >
            {{ item.searchableContent || '' }}
          </a-typography-paragraph>

          <div v-if="item.ocrResults?.length" class="ocr-results">
            <div class="ocr-title">{{ $t('document.ocrResults') }}</div>
            <a-space direction="vertical" size="mini" style="width:100%">
              <div
                v-for="ocr in item.ocrResults"
                :key="ocr.id || index"
                class="ocr-item"
              >
                <span
                  class="ocr-engine"
                  :style="{ color: getEngineColor(ocr.engine || '') }"
                >
                  {{ getEngineAbbr(ocr.engine || '') }}
                </span>

                <span class="ocr-status">
                  <icon-close v-if="ocr.errorMessage" style="color:red" />
                  <icon-check v-else style="color:green" />
                </span>

                <span class="ocr-metrics">
                  {{ ocr.confidenceScore ? (ocr.confidenceScore * 100).toFixed(1) + '%' : 'N/A' }}
                  · {{ ocr.processingTimeMs ? ocr.processingTimeMs + ' ms' : 'N/A' }}
                  · {{ ocr.estimatedCost ?? 'N/A' }}
                </span>
              </div>
            </a-space>

            <!-- Updated Recommendation Display -->
            <div v-if="item?.recommendation" class="ocr-results">
              <div class="markdown-recommendation">
                <div 
                  class="markdown-content"
                  v-html="renderMarkdown(item.recommendation || '')"
                />
              </div>
            </div>
          </div>

          <!-- Processing indicator for current document -->
          <div v-if="isProcessing(item)" class="processing-indicator">
            <a-progress 
              :id="'processing-progress-' + item.id" 
              :percent="item.ocrProgress"
            />
            <div class="processing-text">
              Processing with OCR engines...
            </div>
          </div>
        </div>
        
        <template #actions>
          <a-space fill>
            <a-button 
              type="primary" 
              long 
              @click="parseDoc(item)"
              :loading="isProcessing(item)"
              :disabled="isProcessing(item)"
            >
              <template #icon>
                <icon-loading v-if="isProcessing(item)" spin />
                <icon-translate v-else />
              </template>
              {{ isProcessing(item) ? 'Processing...' : 'Parse' }}
            </a-button>
            <a-button type="primary" long @click="downloadDocument(item)">
              <template #icon>
                <icon-download />
              </template>
              {{ $t('document.operation.download.result') }}
            </a-button>
          </a-space>
        </template>
      </a-card>
    </a-col>
  </a-row>
  <a-pagination
    v-model:current="pagination.current"
    v-model:page-size="pagination.pageSize"
    :total="pagination.total"
    show-total
    show-jumper
    show-page-size
    :page-size-options="[10, 20, 50, 100]"
    @change="onPageChange"
    style="margin-top: 24px; justify-content: center"
  />
</template>

<script lang="ts" setup>
  import { computed, ref, reactive, watch, nextTick, onMounted } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { getToken } from '@/utils/auth';
  import { useRouter } from 'vue-router';
  import useLoading from '@/hooks/loading';
  import { Message } from '@arco-design/web-vue';
  import {
    IconLoading,
    IconTranslate,
    IconDownload,
    IconPlus,
    IconClockCircle,
    IconClose,
    IconCheck,
  } from '@arco-design/web-vue/es/icon';
  import {
    Document,
    DocumentList,
    findDocumentByCondition,
    getUploadUrl,
    getDownloadUrl,
    exportParseResult,
  } from '@/api/document';
  import { marked } from 'marked';
  import DocumentSearchForm from './doc-search-form.vue';
  import { ProgressData } from '../composables/useOcrProgress';
  import { useOcrProgress } from '../composables/useOcrProgress';

  const { setLoading } = useLoading(true);
  const { t, locale } = useI18n();
  const router = useRouter();

  const processingDocuments = ref<Set<string>>(new Set());

  const searchParams: Record<string, any> = reactive({
    current: 1,
    pageSize: 10,
  });
  
  const renderData = ref<Document[]>([]);
  
  const basePagination = {
    current: 1,
    pageSize: 10,
  };

  const pagination = reactive({
    current: 1,
    pageSize: 10,
    total: 0,
  });

  // Helper functions for processing state
  const isProcessing = (document: Document): boolean => {
    return document.status === 'processing' || processingDocuments.value.has(document.id || '');
  };

  const fetchData = async (params: DocumentList = { 
    current: 1, 
    pageSize: 20, 
    searchKeywords: null,
    status: null,
    fromTime: null,
    toTime: null,
    sortBy: null,
    desc: null,
  }) => {
    setLoading(true);
    try {
      const { data } = await findDocumentByCondition(params);
      console.log(data);
      renderData.value = data.documents;
      pagination.current = params.current || 1;
      pagination.total = data.total;
    } catch (err) {
      // Error handling
    } finally {
      setLoading(false);
    }
  };

  const onPageChange = (current: number) => {
    fetchData({ ...basePagination, current } as DocumentList);
  };

  const handleSearch = (formModel: Record<string, any>) => {
    const { createdTime, ...rest } = formModel;
    searchParams.value = {
      ...basePagination,
      ...rest,
    };
    if (createdTime) {
      const [fromTime, toTime] = createdTime;
      searchParams.value.fromTime = fromTime;
      searchParams.value.toTime = toTime;
    }
    fetchData(searchParams.value as DocumentList);
  };

  const handleReset = () => {
    searchParams.value = {
      current: 1,
      pageSize: 10,
    };
    fetchData(searchParams.value as DocumentList);
  };

  const downloadDocument = async (record: Document) => {
    if (!record.id) {
      Message.error('Document ID is missing.');
      return;
    }

    const { data } = await exportParseResult(record.id);
    window.open(getDownloadUrl(data || ''), '_blank');
  };

  // Progress tracking state
  const { connect, sendOCRProgress } = useOcrProgress((progressData: ProgressData) => {
    console.log('Received progress:', progressData);
    if (progressData.document_id) {
      const docToUpdate = renderData.value.find((doc) => doc.id === progressData.document_id);
      if (docToUpdate) {
        docToUpdate.ocrProgress = progressData.percentage;
      }
    }
    if (progressData.completed) {
      processingDocuments.value.delete(progressData.document_id);
      fetchData();
    }
  });

  const parseDoc = async (record: Document) => {
    if (!record.id) {
      Message.error('Document ID is missing.');
      return;
    }

    processingDocuments.value.add(record.id);
    sendOCRProgress(record.id);
  };

  const token = getToken();
  const docFile = ref();

  const onDocChange = (info: any, currentFile: any) => {
    const { status, response } = currentFile;
    docFile.value = { ...currentFile };

    if (status === 'done') {
      if (response?.code === 0 && response?.data) {
        const { data } = response;
        fetchData();
        // Auto-start processing after upload
        parseDoc({ id: data.id } as Document);
      } else if (response?.code === -1) {
        Message.error(response.msg);
      }
      docFile.value = null;
    } else if (status === 'error') {
      Message.error(t('common.upload.failed'));
      docFile.value = null;
    }
  };

  const onDocError = () => {
    docFile.value = null;
  };

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'pending': return 'arcoblue';
      case 'processing': return 'orange';
      case 'completed': return 'green';
      case 'failed': return 'red';
      default: return 'arcoblue';
    }
  };

  const getEngineAbbr = (engine: string) => {
    const abbrMap: Record<string, string> = {
      paddleocr: 'paddleocr',
      tesseract: 'tesseract',
      easyocr: 'easyocr',
      pdfplumber: 'pdfplumber'
    };
    return abbrMap[engine] || engine.substring(0, 3);
  };

  const getEngineColor = (engine: string) => {
    const colorMap: Record<string, string> = {
      paddleocr: '#007bff',
      tesseract: '#001c00',
      easyocr: '#1f7082',
      pdfplumber: '#f5222d'
    };
    return colorMap[engine] || '#007bff';
  };

  const formatFileSize = (bytes: number | null) => {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / k ** i).toFixed(2))} ${sizes[i]}`;
  };

  const formatDate = (dateString: string | null) => {
    return dateString ? new Date(dateString).toLocaleString() : 'N/A';
  };

  // Markdown rendering function
  const renderMarkdown = (text: string): string => {
    if (!text) return '';
    return marked.parse(text) as string;
  };

  onMounted(() => {
    connect();
    fetchData(searchParams.value as DocumentList);
  });
</script>

<style scoped>
.document-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  background-color: var(--color-bg-1);
}

.document-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 14px -4px rgba(0, 0, 0, 0.12);
}

.document-card.processing {
  border: 2px solid #ff7d00;
  box-shadow: 0 0 0 2px rgba(255, 125, 0, 0.1);
}

.card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.document-meta {
  margin: 10px 0 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-2);
}

.meta-value {
  font-weight: 500;
  color: var(--color-text-1);
}

.document-abstract {
  flex: 1;
  overflow: auto;
  margin: 8px 0 14px;
  line-height: 1.6;
  font-size: 13px;
  color: var(--color-text-2);
  max-height: 100px;
}

.processing-indicator {
  margin: 12px 0;
  padding: 8px 0;
  border-top: 1px solid var(--color-border-3);
}

.processing-text {
  font-size: 12px;
  color: var(--color-text-3);
  margin-top: 4px;
  text-align: center;
}

.ocr-results {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--color-border-3);
}

.ocr-title {
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--color-text-2);
}

.ocr-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  background-color: var(--color-fill-2);
  border-radius: 4px;
  font-size: 12px;
}

.ocr-item .ocr-engine {
  font-weight: 500;
}

.ocr-item .ocr-status {
  display: flex;
  align-items: center;
  gap: 3px;
}

.ocr-item .ocr-metrics {
  margin-left: auto;
  font-size: 11px;
  color: var(--color-text-3);
}

.ocr-icon {
  font-size: 10px;
}

/* Markdown recommendation styles */
.markdown-recommendation {
  margin-top: 10px;
  padding: 8px;
  background-color: var(--color-fill-1);
  border-radius: 4px;
}

.markdown-content {
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-text-2);
}

/* Markdown element styling */
.markdown-content h1, 
.markdown-content h2, 
.markdown-content h3 {
  font-weight: 600;
  margin: 12px 0 8px;
}

.markdown-content h1 { font-size: 18px; }
.markdown-content h2 { font-size: 16px; }
.markdown-content h3 { font-size: 14px; }

.markdown-content p {
  margin: 8px 0;
}

.markdown-content ul,
.markdown-content ol {
  padding-left: 24px;
  margin: 8px 0;
}

.markdown-content li {
  margin: 4px 0;
}

.markdown-content strong {
  font-weight: 600;
  color: var(--color-text-1);
}

.markdown-content em {
  font-style: italic;
}

.markdown-content code {
  font-family: monospace;
  background-color: var(--color-fill-2);
  padding: 2px 4px;
  border-radius: 3px;
}

.markdown-content pre {
  background-color: var(--color-fill-2);
  padding: 8px;
  border-radius: 4px;
  overflow: auto;
}

.markdown-content pre code {
  background: none;
  padding: 0;
}

.markdown-content blockquote {
  border-left: 3px solid var(--color-border-3);
  padding-left: 12px;
  margin: 8px 0;
  color: var(--color-text-3);
}

.markdown-content a {
  color: var(--color-link);
  text-decoration: underline;
}
</style>