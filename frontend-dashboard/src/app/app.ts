import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

import { DashboardComponent } from './dashboard/dashboard'; 
import { ChatComponent } from './chat/chat'; 
import { TeamComponent } from './team/team';       
import { SettingsComponent } from './settings/settings'; 
import { LoginComponent } from './login/login'; 
import { AiService } from './ai.service'; 
import { ChangeDetectorRef } from '@angular/core'; //

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, DashboardComponent, ChatComponent, TeamComponent, SettingsComponent, LoginComponent],
  template: `
    <div *ngIf="showLoginModal" class="login-overlay">
      <app-login (loginSuccess)="onLoginSuccess()" (cancel)="showLoginModal = false"></app-login>
    </div>

    <div style="height: 100vh;">
      
      <app-dashboard 
        *ngIf="currentView === 'dashboard'" 
        (navigate)="onNavigate($event)">
      </app-dashboard>
      
      <app-chat 
        *ngIf="currentView === 'chat' && isAuthenticated" 
        (navigate)="onNavigate($event)">
      </app-chat>
      
      <app-team 
        *ngIf="currentView === 'team' && isAuthenticated" 
        (goBack)="onNavigate('dashboard')">
      </app-team>
      
      <app-settings 
        *ngIf="currentView === 'settings' && isAuthenticated" 
        (goBack)="onNavigate('dashboard')">
      </app-settings>

    </div>
  `,
  styles: [`
    .login-overlay {
      position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
      z-index: 9999; background: rgba(0,0,0,0.5);
      animation: fadeIn 0.2s ease-out;
    }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  `]
})
export class App {
  isAuthenticated = false;
  showLoginModal = false; // Controls the popup
  currentView: string = 'dashboard';

  constructor(private aiService: AiService, private cdr: ChangeDetectorRef) { //
    this.isAuthenticated = this.aiService.isLoggedIn();
  }

  onLoginSuccess() {
    this.isAuthenticated = true;
    this.showLoginModal = false; // Close modal
    // Determine where to go? For now, stay on dashboard or the requested view.
  }

  onNavigate(view: string) {
    console.log('User clicked:', view);

    // 1. ALLOW Dashboard (Public Preview)
    if (view === 'dashboard') {
      this.currentView = 'dashboard';
      return;
    }

    // 2. CHECK AUTH for EVERYTHING ELSE
    if (!this.isAuthenticated) {
      this.showLoginModal = true; // ⛔ STOP! Show Login
      return; 
    }

    // 3. If Logged In, Handle External Links
    if (view === 'tasks' || view === 'workflow' || view === 'slack') {
      this.openExternalLink(view);
      return;
    }

    // 4. Handle Logout
    if (view === 'logout') {
      this.aiService.logout();
      this.isAuthenticated = false;
      
      // 🚀 THE FIX: Instead of showing a broken dashboard, show the Login screen
      this.showLoginModal = true; 
      this.currentView = 'dashboard'; // Keep dashboard as the background view
      return;
    }
    // 5. Allow Internal Navigation
    this.currentView = view;
  }

  openExternalLink(type: string) {
    const savedLinks = localStorage.getItem('nexus_links');
    const links = savedLinks ? JSON.parse(savedLinks) : {};
    let url = type === 'tasks' ? links.trello : type === 'workflow' ? links.n8n : links.slack;

    if (url) window.open(url, '_blank');
    else {
      if (confirm(`⚠️ No ${type.toUpperCase()} link found! Go to Settings?`)) this.currentView = 'settings';
    }
  }

  switchView(view: string) {
    this.currentView = view;
  }
}
