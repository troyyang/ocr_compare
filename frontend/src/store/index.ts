import { createPinia } from 'pinia';
import useAppStore from './modules/app';
import useUserStore from './modules/user';
import useTabBarStore from './modules/tab-bar';
import useDocumentStore from './modules/document';

const pinia = createPinia();

export { useAppStore, useUserStore, useTabBarStore, useDocumentStore };
export default pinia;
