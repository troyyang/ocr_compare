import { DEFAULT_LAYOUT } from '../base';
import { AppRouteRecordRaw } from '../types';

const OCR_COMPARE: AppRouteRecordRaw = {
  path: '/ocr-compare',
  name: 'ocr-compare',
  component: DEFAULT_LAYOUT,
  meta: {
    locale: 'menu.ocr-compare',
    requiresAuth: true,
    icon: 'icon-storage',
    order: 0,
  },
  children: [
    {
      path: 'document',
      name: 'Document',
      component: () => import('@/views/ocr-compare/document/index.vue'),
      meta: {
        locale: 'menu.ocr-compare.document',
        requiresAuth: true,
      },
    },
  ],
};

export default OCR_COMPARE;
