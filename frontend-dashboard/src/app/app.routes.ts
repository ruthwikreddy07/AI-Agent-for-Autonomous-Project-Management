import { Routes } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard.ts'; // Matches your folder
import { ChatComponent } from './chat/chat.ts';           // Matches your folder
import { TeamComponent } from './team/team.ts';           // Matches your folder
import { SettingsComponent } from './settings/settings.ts'; // Matches your folder
import { LoginComponent } from './login/login.ts';         // Matches your folder

export const routes: Routes = [
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'chat', component: ChatComponent },
  { path: 'team', component: TeamComponent },
  { path: 'settings', component: SettingsComponent },
  { path: '**', redirectTo: 'dashboard' } 
];