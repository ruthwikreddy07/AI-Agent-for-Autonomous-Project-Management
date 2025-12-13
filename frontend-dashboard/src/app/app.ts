import { Component, OnInit, AfterViewChecked, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService } from './ai.service';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

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
  // ✅ ADDED: Track Login vs Sign Up mode
  isLoginMode: boolean = true; 
  
  currentView: 'chat' | 'settings' = 'chat';
  userMessage: string = '';
  chatHistory: { sender: string, text: string }[] = [];
  realRisks: string[] = [];
  employees: any[] = [];
  
  loginData = { username: '', password: '' };
  // Added 'rate' with a default of 50
  newEmp = { name: '', role: '', skills: '', email: '', rate: 50 };
  
  isLoading: boolean = false;
  showApprovalButtons: boolean = false;

  constructor(private aiService: AiService, private sanitizer: DomSanitizer) {}

  ngOnInit() {
    this.isAuthenticated = this.aiService.isLoggedIn();
    if (this.isAuthenticated) this.initDashboard();
  }

  // --- AUTHENTICATION LOGIC (UPDATED) ---

  // 1. Switch between Login and Sign Up views
  toggleAuthMode() {
    this.isLoginMode = !this.isLoginMode;
    this.loginData = { username: '', password: '' }; // Clear inputs
  }

  // 2. Main Auth Handler (Connects to HTML button)
  onAuthAction() {
    if (!this.loginData.username || !this.loginData.password) {
      alert('⚠️ Please enter both username and password');
      return;
    }

    if (this.isLoginMode) {
      // --- LOGIN ---
      this.aiService.login(this.loginData.username, this.loginData.password).subscribe({
        next: () => { 
          this.isAuthenticated = true; 
          this.initDashboard(); 
        },
        error: () => alert('❌ Invalid Credentials!')
      });
    } else {
      // --- REGISTER (New Logic) ---
      this.aiService.register(this.loginData.username, this.loginData.password).subscribe({
        next: () => { 
          alert('✅ Account Created! Please login.');
          this.isLoginMode = true; // Switch back to login screen
        },
        error: (err) => {
          if (err.status === 400) alert('⚠️ Username already exists.');
          else alert('❌ Registration failed. Try again.');
        }
      });
    }
  }

  // --- EXISTING LOGIC BELOW (UNCHANGED) ---

  onLogout() { this.aiService.logout(); this.isAuthenticated = false; this.chatHistory = []; }

  formatText(text: string): SafeHtml {
    let formatted = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') 
      .replace(/\n/g, '<br>'); 
    return this.sanitizer.bypassSecurityTrustHtml(formatted);
  }

  initDashboard() {
    this.fetchRisks();
    this.loadEmployees();
    this.scrollToBottom();
  }

  ngAfterViewChecked() { this.scrollToBottom(); }
  scrollToBottom() { try { this.myScrollContainer.nativeElement.scrollTop = this.myScrollContainer.nativeElement.scrollHeight; } catch(err) { } }
  switchView(view: 'chat' | 'settings') { this.currentView = view; }

  sendMessage() {
    if (!this.userMessage.trim()) return;
    this.chatHistory.push({ sender: 'You', text: this.userMessage });
    const msg = this.userMessage;
    this.userMessage = ''; 
    this.isLoading = true; 
    this.showApprovalButtons = false;

    this.aiService.sendMessage(msg).subscribe({
      next: (res: any) => {
        this.chatHistory.push({ sender: 'AI Agent', text: res.reply });
        this.isLoading = false;
        if (res.approval_required) this.showApprovalButtons = true;
        this.fetchRisks();
      },
      error: () => { 
        this.chatHistory.push({ sender: 'System', text: '⚠️ Connection Error. Ensure Backend is running.' }); 
        this.isLoading = false; 
      }
    });
  }

  loadEmployees() { this.aiService.getEmployees().subscribe(data => this.employees = data); }

  addEmployee() {
    if (!this.newEmp.name || !this.newEmp.email) {
      alert('⚠️ Name and Email are required!');
      return;
    }

    const empData = {
      ...this.newEmp,
      // Handle skills split safely
      skills: typeof this.newEmp.skills === 'string' 
        ? (this.newEmp.skills as string).split(',') 
        : this.newEmp.skills
    };

    // We now pass 'this.newEmp.rate' as the last argument
    this.aiService.addEmployee(
      empData.name, 
      empData.role, 
      empData.skills, 
      empData.email, 
      empData.rate
    ).subscribe({
      next: (res) => {
        alert(res.msg);
        // Reset form (including rate reset to 50)
        this.newEmp = { name: '', role: '', skills: '', email: '', rate: 50 };
        this.loadEmployees();
      },
      error: () => alert('Error adding employee')
    });
  }

  fetchRisks() { this.aiService.getRisks().subscribe(res => this.realRisks = res.risks); }
  
  onApprove() {
    this.showApprovalButtons = false; 
    this.isLoading = true;
    this.aiService.approvePlan().subscribe(() => {
      this.chatHistory.push({ sender: 'System', text: '✅ Plan Authorized. Executing...' });
      this.isLoading = false;
      this.fetchRisks();
    });
  }
  
  onReject() {
    this.showApprovalButtons = false;
    this.aiService.rejectPlan().subscribe(() => this.chatHistory.push({ sender: 'System', text: '❌ Plan Cancelled.' }));
  }
}