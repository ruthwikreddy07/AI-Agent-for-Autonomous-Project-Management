import { Routes } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard'; // 🚀 Remove .ts
import { ChatComponent } from './chat/chat';           // 🚀 Remove .ts
import { TeamComponent } from './team/team';           // 🚀 Remove .ts
import { SettingsComponent } from './settings/settings'; // 🚀 Remove .ts
import { LoginComponent } from './login/login';         // 🚀 Remove .ts

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'chat', component: ChatComponent },
  { path: 'team', component: TeamComponent },
  { path: 'settings', component: SettingsComponent },
  { path: '**', redirectTo: 'dashboard' } 
];