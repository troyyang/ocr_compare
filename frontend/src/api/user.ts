import axios from 'axios';
import type { RouteRecordNormalized } from 'vue-router';

// frontend/src/api/user.ts
export interface UserRecord {
  id: string | null;
  username: string;
  email: string;
  mobile: string;
  password: string;
  createTime: string | null;
  updateTime: string | null;
  role: string | null;
  // Add missing properties
  name?: string;
  avatar?: string;
  jobName?: string;
  organizationName?: string;
  locationName?: string;
  certification?: string;
  accountId?: string | number;
  registrationDate?: string;
  [key: string]: any; // For any additional dynamic properties
}

export interface Department {
  value: string;
  parentId: string | null;
  weight: number;
  label: string;
  children: Department[];
}

export interface Staff {
  id: string;
  no: string;
  loginName: string;
  name: string;
  type: string;
  email: string;
}

export interface PersonResult {
  department: {name: string; id: string};
  persons: Staff[];
  posts: any[];
}

export interface UserParams {
  keyword: string;
  role: string;
  startTime: string;
  endTime: string;
  current: number | null;
  pageSize: number | null;
}

export interface LoginData {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  password: string;
  email: string;
}

export interface LoginRes {
  token: string;
}

export interface UpdateUserPasswordRes {
  orgPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export function login(data: LoginData) {
  return axios.post<LoginRes>('/api/auth/login', data);
}

export function register(data: RegisterData) {
  return axios.post<LoginRes>('/api/auth/register', data);
}

export function logout() {
  return axios.post<LoginRes>('/api/auth/logout');
}

export function getUserInfo() {
  return axios.post<UserRecord>('/api/auth/info');
}

export function updateUserInfo(data: UserRecord) {
  return axios.put<UserRecord>('/api/auth/update', data);
}

export function updateUserPassword(data: UpdateUserPasswordRes) {
  return axios.put<UserRecord>('/api/auth/update/password', data);
}

export function getMenuList() {
  return axios.post<RouteRecordNormalized[]>('/api/auth/menu');
}

// for admin user
export function queryUserList(userParams: UserParams) {
  return axios.post('/api/users/list', userParams);
}

export function saveUser(data: UserRecord) {
  return axios.put('/api/users', data);
}

export function deleteUser(id: number) {
  return axios.delete(`/api/users/${id}`);
}

export function departmentTree() {
  return axios.get<Department[]>('/api/users/department/tree');
}

export function staffsByDepartmentId(departmentId: string) {
  return axios.get<PersonResult>(`/api/users/department/staffs/${departmentId}`);
}