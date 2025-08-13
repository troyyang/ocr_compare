import localeMessageBox from '@/components/message-box/locale/zh-CN';
import localeLogin from '@/views/login/locale/zh-CN';

import localeSuccess from '@/views/result/success/locale/zh-CN';
import localeError from '@/views/result/error/locale/zh-CN';

import locale403 from '@/views/exception/403/locale/zh-CN';
import locale404 from '@/views/exception/404/locale/zh-CN';
import locale500 from '@/views/exception/500/locale/zh-CN';

import localeUserInfo from '@/views/user/info/locale/zh-CN';
import localeUserSetting from '@/views/user/setting/locale/zh-CN';

import localeManual from '@/views/ocr-compare/document/locale/zh-CN';

import localeCommon from './zh-CN/common';
import localeSettings from './zh-CN/settings';

export default {
  'app.title': 'OCR Compare',
  'menu.list': '列表页',
  'menu.result': '结果页',
  'menu.exception': '异常页',
  'menu.form': '表单页',
  'menu.profile': '详情页',
  'menu.user': '个人中心',
  'menu.ocr-compare': 'OCR Compare',
  'menu.ocr-compare.document': 'Document',
  'menu.api': 'API',
  'navbar.docs': '文档中心',
  'navbar.action.locale': '切换为中文',
  
  ...localeCommon,
  ...localeSettings,
  ...localeMessageBox,
  ...localeLogin,

  ...localeSuccess,
  ...localeError,
  ...locale403,
  ...locale404,
  ...locale500,
  ...localeUserInfo,
  ...localeUserSetting,

  ...localeManual,
};
