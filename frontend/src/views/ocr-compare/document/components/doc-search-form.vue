<template>
  <div>
    <a-row>
      <a-col :flex="1">
        <a-form
          :model="formModel"
          :label-col-props="{ span: 6 }"
          :wrapper-col-props="{ span: 18 }"
          label-align="left"
        >
          <a-row :gutter="16">
            <!-- Basic Information -->
            <a-col :span="8">
              <a-form-item field="searchKeywords" :label="$t('document.search')">
                <a-input v-model="formModel.searchKeywords" :placeholder="$t('document.search.placeholder')" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item field="status" :label="$t('document.status')">
                <a-select v-model="formModel.status" :placeholder="$t('document.status.placeholder')">
                  <a-option v-for="status in documentStatusOptions" :key="status.value" :value="status.value">
                    {{ $t(`document.status.${status.value}`) }}
                  </a-option>
                </a-select>
              </a-form-item>
            </a-col>
            <!-- Date --> 
            <a-col :span="8">
              <a-form-item field="createdTime" :label="$t('document.createdTime')">
                <a-range-picker v-model="formModel.createdTime" style="width: 100%" />
              </a-form-item>
            </a-col>
          </a-row>
        </a-form>
      </a-col>
      <a-divider style="height: 84px" direction="vertical" />
      <a-col :flex="'86px'" style="text-align: right">
        <a-space direction="vertical" :size="18">
          <a-button type="primary" @click="handleSearch">
            <template #icon>
              <icon-search />
            </template>
            {{ $t('common.search') }}
          </a-button>
          <a-button @click="handleReset">
            <template #icon>
              <icon-refresh />
            </template>
            {{ $t('common.reset') }}
          </a-button>
        </a-space>
      </a-col>
    </a-row>
  </div>
</template>

<script lang="ts" setup>
  import { ref, onMounted } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { DocumentStatus } from '@/api/document';

  const { t } = useI18n();

  const emit = defineEmits(['search', 'reset']);

  // Form model definition
  const formModel = ref({
    searchKeywords: '',
    status: '',
    createdTime: [] as any[],
  });

  const documentStatusOptions = ref([
    { value: DocumentStatus.pending, label: t('document.status.pending') },
    { value: DocumentStatus.processing, label: t('document.status.processing') },
    { value: DocumentStatus.completed, label: t('document.status.completed') },
    { value: DocumentStatus.failed, label: t('document.status.failed') },
  ]);

  // Handle search action
  const handleSearch = () => {
    emit('search', formModel.value);
  };

  // Handle reset action
  const handleReset = () => {
    formModel.value = {
      searchKeywords: '',
      status: '',
      createdTime: [],
    };
    emit('reset');
  };
  // Initialize component
  onMounted(() => {
    // init form model
    formModel.value = {
      searchKeywords: '',
      status: '',
      createdTime: [],
    };
  });

  // Expose form model for parent access
  defineExpose({ formModel });
</script>

<style scoped>
.arco-col {
  margin-bottom: 16px;
}
</style>