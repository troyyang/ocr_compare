<template>
  <div class="ocr-comparison">
    <a-card title="OCR Engine Comparison" class="comparison-card">
      <template #extra>
        <a-space>
          <a-button 
            type="primary" 
            size="small"
            @click="refreshResults"
            :loading="refreshing"
          >
            <template #icon>
              <icon-refresh />
            </template>
            Refresh
          </a-button>
          <a-button 
            size="small"
            @click="exportResults"
          >
            <template #icon>
              <icon-download />
            </template>
            Export
          </a-button>
        </a-space>
      </template>

      <!-- Document Info -->
      <div class="document-info" v-if="document">
        <a-descriptions :column="3" size="small" bordered>
          <a-descriptions-item label="Filename">
            {{ document.filename }}
          </a-descriptions-item>
          <a-descriptions-item label="File Type">
            {{ document.fileType }}
          </a-descriptions-item>
          <a-descriptions-item label="File Size">
            {{ formatFileSize(document.fileSize) }}
          </a-descriptions-item>
          <a-descriptions-item label="Status">
            <a-tag :color="getStatusColor(document.status)">
              {{ $t(`document.status.${document.status}`) }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="Upload Time">
            {{ formatDate(document.createdAt) }}
          </a-descriptions-item>
          <a-descriptions-item label="Pages">
            {{ getTotalPages() }}
          </a-descriptions-item>
        </a-descriptions>
      </div>

      <!-- OCR Results Comparison -->
      <div class="ocr-results" v-if="ocrResults.length > 0">
        <a-divider>OCR Engine Results</a-divider>
        
        <a-row :gutter="16">
          <a-col 
            v-for="result in ocrResults" 
            :key="result.id"
            :xs="24" 
            :sm="12" 
            :md="8"
            :lg="6"
          >
            <a-card 
              class="engine-result-card"
              :class="{ 'best-result': isBestResult(result) }"
              size="small"
            >
              <template #title>
                <div class="engine-header">
                  <span class="engine-name">{{ getEngineName(result.engine) }}</span>
                  <a-tag 
                    v-if="isBestResult(result)" 
                    color="green" 
                    size="small"
                  >
                    Best
                  </a-tag>
                </div>
              </template>

              <div class="result-content">
                <!-- Text Preview -->
                <div class="text-preview">
                  <a-typography-title :heading="6" style="margin-bottom: 8px">
                    Text Preview (First 300 chars)
                  </a-typography-title>
                  <a-typography-paragraph 
                    :ellipsis="{ rows: 3, expandable: true }"
                    class="preview-text"
                  >
                    {{ result.extractedText || 'No text extracted' }}
                  </a-typography-paragraph>
                </div>

                <!-- Performance Metrics -->
                <div class="performance-metrics">
                  <a-typography-title :heading="6" style="margin-bottom: 8px">
                    Performance Metrics
                  </a-typography-title>
                  
                  <a-space direction="vertical" size="mini" style="width: 100%">
                    <!-- Confidence Score -->
                    <div class="metric-item">
                      <span class="metric-label">Confidence:</span>
                      <a-progress 
                        :percent="getConfidencePercent(result.confidenceScore)" 
                        :color="getConfidenceColor(result.confidenceScore)"
                        size="small"
                        :show-text="false"
                      />
                      <span class="metric-value">
                        {{ getConfidencePercent(result.confidenceScore) }}%
                      </span>
                    </div>

                    <!-- Processing Time -->
                    <div class="metric-item">
                      <span class="metric-label">Processing Time:</span>
                      <span class="metric-value">
                        {{ formatProcessingTime(result.processingTimeMs) }}
                      </span>
                    </div>

                    <!-- Text Length -->
                    <div class="metric-item">
                      <span class="metric-label">Text Length:</span>
                      <span class="metric-value">
                        {{ formatTextLength(result.extractedText) }}
                      </span>
                    </div>

                    <!-- Estimated Cost -->
                    <div class="metric-item" v-if="result.estimatedCost !== null">
                      <span class="metric-label">Estimated Cost:</span>
                      <span class="metric-value">
                        ${{ formatCost(result.estimatedCost) }}
                      </span>
                    </div>

                    <!-- Error Message -->
                    <div class="error-message" v-if="result.errorMessage">
                      <a-alert 
                        type="error" 
                        :message="result.errorMessage"
                        size="small"
                        show-icon
                      />
                    </div>
                  </a-space>
                </div>

                <!-- Page Metrics -->
                <div class="page-metrics" v-if="result.pageMetrics">
                  <a-typography-title :heading="6" style="margin-bottom: 8px">
                    Page Details
                  </a-typography-title>
                  <a-descriptions :column="1" size="small">
                    <a-descriptions-item label="Pages Processed">
                      {{ result.pageMetrics.pages_processed || 1 }}
                    </a-descriptions-item>
                    <a-descriptions-item label="Text Length">
                      {{ result.pageMetrics.text_length || 0 }} chars
                    </a-descriptions-item>
                  </a-descriptions>
                </div>
              </div>
            </a-card>
          </a-col>
        </a-row>

        <!-- Recommendation Summary -->
        <div class="recommendation-summary" v-if="document?.recommendation">
          <a-divider>Recommendation</a-divider>
          <a-alert 
            type="success" 
            :message="document.recommendation"
            show-icon
            closable
          />
        </div>
      </div>

      <!-- No Results State -->
      <div class="no-results" v-else-if="document && document.status === 'completed'">
        <a-empty description="No OCR results available">
          <template #image>
            <icon-file-exclamation />
          </template>
        </a-empty>
      </div>

      <!-- Processing State -->
      <div class="processing-state" v-else-if="document && document.status === 'processing'">
        <a-result
          status="info"
          title="OCR Processing in Progress"
          sub-title="Please wait while the document is being processed by multiple OCR engines."
        >
          <template #extra>
            <a-progress 
              :percent="processingProgress" 
              status="normal"
              :show-text="false"
            />
            <div style="margin-top: 8px; text-align: center;">
              {{ processingStatus }}
            </div>
          </template>
        </a-result>
      </div>

      <!-- Error State -->
      <div class="error-state" v-else-if="document && document.status === 'failed'">
        <a-result
          status="error"
          title="OCR Processing Failed"
          sub-title="The document could not be processed. Please try again or contact support."
        >
          <template #extra>
            <a-button type="primary" @click="retryProcessing">
              Retry Processing
            </a-button>
          </template>
        </a-result>
      </div>
    </a-card>
  </div>
</template>

<script lang="ts" setup>
  import { ref, computed, onMounted, watch } from 'vue'
  import { Message } from '@arco-design/web-vue'
  import { 
    IconRefresh, 
    IconDownload, 
    IconExclamation,
    IconCheck,
    IconClose
  } from '@arco-design/web-vue/es/icon'
  import { useI18n } from 'vue-i18n'

  const { t } = useI18n()

  // Props
  interface Props {
    documentId?: string
    document?: any
    ocrResults?: any[]
  }

  // Emits
  const emit = defineEmits<{
    refresh: []
    export: []
    retry: []
  }>()


  const props = withDefaults(defineProps<Props>(), {
    documentId: '',
    document: null,
    ocrResults: () => []
  })

  // Reactive state
  const refreshing = ref(false)
  const processingProgress = ref(0)
  const processingStatus = ref('Initializing...')

  // Computed properties
  const document = computed(() => props.document)
  const ocrResults = computed(() => props.ocrResults || [])

  // Methods
  const getEngineName = (engine: string) => {
    const engineNames: Record<string, string> = {
      'paddleocr': 'PaddleOCR',
      'tesseract': 'Tesseract',
      'easyocr': 'EasyOCR',
      'pdfplumber': 'PDFPlumber'
    }
    return engineNames[engine] || engine.toUpperCase()
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      'pending': 'orange',
      'processing': 'blue',
      'completed': 'green',
      'failed': 'red'
    }
    return colors[status] || 'default'
  }

  const getTotalPages = () => {
    if (!ocrResults.value.length) return 1
    const firstResult = ocrResults.value[0]
    return firstResult.pageMetrics?.pages_processed || 1
  }

  const isBestResult = (result: any) => {
    if (!ocrResults.value.length) return false
    // Find the result with highest confidence
    const bestResult = ocrResults.value.reduce((best, current) => {
      if (!current.errorMessage && current.confidenceScore > best.confidenceScore) {
        return current
      }
      return best
    })
    return result.id === bestResult.id
  }

  const getConfidencePercent = (confidence: number) => {
    if (confidence === null || confidence === undefined) return 0
    return Math.round(confidence * 100)
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return '#52c41a' // Green
    if (confidence >= 0.6) return '#faad14' // Orange
    return '#f5222d' // Red
  }

  const formatProcessingTime = (timeMs: number) => {
    if (!timeMs) return 'N/A'
    if (timeMs < 1000) return `${timeMs}ms`
    return `${(timeMs / 1000).toFixed(2)}s`
  }

  const formatTextLength = (text: string) => {
    if (!text) return '0 chars'
    return `${text.length} chars`
  }

  const formatCost = (cost: number) => {
    if (cost === null || cost === undefined) return '0.0000'
    return cost.toFixed(4)
  }

  const refreshResults = async () => {
    refreshing.value = true
    try {
      // Emit refresh event to parent
      emit('refresh')
      Message.success('Results refreshed successfully')
    } catch (error) {
      Message.error('Failed to refresh results')
    } finally {
      refreshing.value = false
    }
  }

  const exportResults = () => {
    // Emit export event to parent
    emit('export');
    Message.info('Export functionality will be implemented')
  }

  const retryProcessing = () => {
    // Emit retry event to parent
    emit('retry');
    Message.info('Retry functionality will be implemented')
  }

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

  // Lifecycle
  onMounted(() => {
    // Initialize component
  })

  // Watch for document changes to update processing state
  watch(document, (newDoc) => {
    if (newDoc?.status === 'processing') {
      // Simulate progress updates (in real app, this would come from WebSocket)
      const interval = setInterval(() => {
        if (processingProgress.value < 90) {
          processingProgress.value += Math.random() * 10
          processingStatus.value = 'Processing OCR engines...'
        } else {
          clearInterval(interval)
        }
      }, 1000)
    }
  }, { immediate: true })
</script>

<style scoped lang="less">
  .ocr-comparison {
    .comparison-card {
      margin-bottom: 16px;
    }

    .document-info {
      margin-bottom: 16px;
    }

    .ocr-results {
      margin-top: 16px;
    }

    .engine-result-card {
      height: 100%;
      transition: all 0.3s ease;

      &.best-result {
        border: 2px solid #52c41a;
        box-shadow: 0 4px 12px rgba(82, 196, 26, 0.2);
      }

      .engine-header {
        display: flex;
        align-items: center;
        justify-content: space-between;

        .engine-name {
          font-weight: 600;
          color: #1d2129;
        }
      }

      .result-content {
        .text-preview {
          margin-bottom: 16px;

          .preview-text {
            background: #f7f8fa;
            padding: 8px;
            border-radius: 4px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 12px;
            line-height: 1.4;
          }
        }

        .performance-metrics {
          margin-bottom: 16px;

          .metric-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;

            .metric-label {
              min-width: 100px;
              font-size: 12px;
              color: #4e5969;
            }

            .metric-value {
              font-weight: 600;
              color: #1d2129;
            }
          }
        }

        .page-metrics {
          margin-bottom: 16px;
        }

        .error-message {
          margin-top: 8px;
        }
      }
    }

    .recommendation-summary {
      margin-top: 24px;
    }

    .no-results,
    .processing-state,
    .error-state {
      text-align: center;
      padding: 40px 0;
    }
  }
</style> 