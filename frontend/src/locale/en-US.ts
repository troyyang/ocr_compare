import localeMessageBox from '@/components/message-box/locale/en-US';
import localeLogin from '@/views/login/locale/en-US';

import localeSuccess from '@/views/result/success/locale/en-US';
import localeError from '@/views/result/error/locale/en-US';

import locale403 from '@/views/exception/403/locale/en-US';
import locale404 from '@/views/exception/404/locale/en-US';
import locale500 from '@/views/exception/500/locale/en-US';

import localeUserInfo from '@/views/user/info/locale/en-US';
import localeUserSetting from '@/views/user/setting/locale/en-US';

import localeManual from '@/views/ocr-compare/document/locale/en-US';

import localeCommon from './en-US/common';
import localeSettings from './en-US/settings';

export default {
  'app.title': 'OCR Compare',
  'menu.dashboard': 'Dashboard',
  'menu.list': 'List',
  'menu.result': 'Result',
  'menu.exception': 'Exception',
  'menu.form': 'Form',
  'menu.profile': 'Profile',
  'menu.user': 'User Center',
  'menu.faq': 'FAQ',
  'menu.ocr-compare': 'OCR Compare',
  'menu.ocr-compare.document': 'Document',
  'menu.api': 'API',
  'navbar.docs': 'Docs',
  'navbar.action.locale': 'Switch to English',
  
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
