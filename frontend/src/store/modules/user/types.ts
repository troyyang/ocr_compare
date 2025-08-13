import { UserRecord, Department } from '@/api/user';

export type RoleType = '' | '*' | 'admin' | 'user';
export interface UserState {
  currentUser: UserRecord;
  selectedUser?: UserRecord;
  role: RoleType;
}
