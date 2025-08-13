<template>
  <div class="container">
    <Breadcrumb :items="['menu.ocr-compare', 'menu.ocr-compare.document']" />
    <DocCards />
  </div>
</template>

<script lang="ts" setup>
  import DocCards from './components/doc-cards.vue';
</script>

<script lang="ts">
  export default {
    name: 'ManualSearch',
  };
</script>

<style scoped lang="less">
  .container {
    padding: 20px;
  }
</style>
