import { Component, OnInit, AfterViewChecked, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService } from './ai.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.html',
  styleUrls: ['./app.css']
})
export class App implements OnInit, AfterViewChecked {
  @ViewChild('scrollMe') private myScrollContainer!: ElementRef;

  isAuthenticated: boolean = false;
  currentView: 'chat' | 'settings' = 'chat';
  userMessage: string = '';
  chatHistory: { sender: string, text: string }[] = [];
  realRisks: string[] = [];
  employees: any[] = [];
  
  loginData = { username: '', password: '' };
  
  // UPDATED MODEL (Use Email)
  newEmp = { name: '', role: '', skills: '', email: '' };
  
  isLoading: boolean = false;
  showApprovalButtons: boolean = false;

  constructor(private aiService: AiService) {}

  ngOnInit() {
    this.isAuthenticated = this.aiService.isLoggedIn();
    if (this.isAuthenticated) this.initDashboard();
  }

  initDashboard() {
    this.fetchRisks();
    this.loadEmployees();
    this.scrollToBottom();
  }

  ngAfterViewChecked() { this.scrollToBottom(); }
  scrollToBottom() { try { this.myScrollContainer.nativeElement.scrollTop = this.myScrollContainer.nativeElement.scrollHeight; } catch(err) { } }

  onLogin() {
    this.aiService.login(this.loginData.username, this.loginData.password).subscribe({
      next: () => { this.isAuthenticated = true; this.initDashboard(); },
      error: () => alert('Invalid Credentials!')
    });
  }

  onLogout() { this.aiService.logout(); this.isAuthenticated = false; this.chatHistory = []; }
  switchView(view: 'chat' | 'settings') { this.currentView = view; }

  sendMessage() {
    if (!this.userMessage.trim()) return;
    this.chatHistory.push({ sender: 'You', text: this.userMessage });
    const msg = this.userMessage;
    this.userMessage = ''; this.isLoading = true; this.showApprovalButtons = false;

    this.aiService.sendMessage(msg).subscribe({
      next: (res: any) => {
        this.chatHistory.push({ sender: 'AI Agent', text: res.reply });
        this.isLoading = false;
        if (res.approval_required) this.showApprovalButtons = true;
        this.fetchRisks();
      },
      error: () => { this.chatHistory.push({ sender: 'System', text: '⚠️ Error.' }); this.isLoading = false; }
    });
  }

  loadEmployees() { this.aiService.getEmployees().subscribe(data => this.employees = data); }

  addEmployee() {
    // UPDATED VALIDATION
    if (!this.newEmp.name || !this.newEmp.email) { 
      alert('⚠️ Name and Email are required!'); 
      return; 
    }
    this.aiService.addEmployee(this.newEmp.name, this.newEmp.role, this.newEmp.skills, this.newEmp.email).subscribe({
      next: (res) => { alert(res.msg); this.newEmp = { name: '', role: '', skills: '', email: '' }; this.loadEmployees(); },
      error: () => alert('Error adding employee')
    });
  }

  fetchRisks() { this.aiService.getRisks().subscribe(res => this.realRisks = res.risks); }
  
  onApprove() {
    this.showApprovalButtons = false; this.isLoading = true;
    this.aiService.approvePlan().subscribe(() => {
      this.chatHistory.push({ sender: 'System', text: '✅ Plan Executed!' });
      this.isLoading = false;
      this.fetchRisks();
    });
  }
  
  onReject() {
    this.showApprovalButtons = false;
    this.aiService.rejectPlan().subscribe(() => this.chatHistory.push({ sender: 'System', text: '❌ Cancelled.' }));
  }
}