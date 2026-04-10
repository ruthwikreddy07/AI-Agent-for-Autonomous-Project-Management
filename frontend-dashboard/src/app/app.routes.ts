import { Routes } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard';
import { ChatComponent } from './chat/chat';
import { TeamComponent } from './team/team';
import { SettingsComponent } from './settings/settings';
import { LoginComponent } from './login/login';
import { BacklogComponent } from './backlog/backlog';
import { TimelineComponent } from './timeline/timeline';
import { RiskMatrixComponent } from './risk-matrix/risk-matrix';
import { LandingComponent } from './landing/landing';

export const routes: Routes = [
  { path: '', component: LandingComponent },
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'chat', component: ChatComponent },
  { path: 'team', component: TeamComponent },
  { path: 'settings', component: SettingsComponent },
  { path: 'backlog', component: BacklogComponent },
  { path: 'timeline', component: TimelineComponent },
  { path: 'risks', component: RiskMatrixComponent },
  { path: '**', redirectTo: 'dashboard' } 
];