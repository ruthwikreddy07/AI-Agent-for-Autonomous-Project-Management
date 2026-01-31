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
  isLoginMode: boolean = true;
  
  // ✅ 1. MULTI-CHAT VARIABLES
  sessionId: string = ''; 
  savedSessions: { id: string, label: string }[] = []; 

  currentView: 'chat' | 'settings' = 'chat';
  userMessage: string = '';
  chatHistory: { sender: string, text: string }[] = [];
  realRisks: string[] = [];
  employees: any[] = [];
  
  loginData = { username: '', password: '' };
  newEmp = { name: '', role: '', skills: '', email: '', rate: 50 };
  
  isLoading: boolean = false;
  showApprovalButtons: boolean = false;

  constructor(private aiService: AiService, private sanitizer: DomSanitizer) {}

  ngOnInit() {
    this.isAuthenticated = this.aiService.isLoggedIn();
    
    // ✅ ADD THIS BLOCK: Recover username from storage
    const storedUser = localStorage.getItem('current_user');
    if (storedUser) {
      this.loginData.username = storedUser;
    }

    if (this.isAuthenticated) this.initDashboard();
  }

  // ✅ 2. INIT DASHBOARD (Loads Chat List)
  initDashboard() {
    this.loadSessionList(); // Load past chats from browser
    
    // If no chats exist, create the first one automatically
    if (this.savedSessions.length === 0) {
      this.startNewChat(); 
    } else {
      // Otherwise, load the most recent conversation
      this.selectSession(this.savedSessions[0]);
    }

    this.fetchRisks();
    this.loadEmployees();
  }

  // ✅ 3. START NEW CHAT Logic
  startNewChat() {
    const timestamp = new Date().getTime();
    // Create unique ID: "session-username-123456"
    const newId = `session-${this.loginData.username}-${timestamp}`;
    
    const newSession = { 
      id: newId, 
      label: `Chat ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}` 
    };

    this.savedSessions.unshift(newSession); // Add to top of list
    this.saveSessionList(); // Save to LocalStorage
    this.selectSession(newSession); // Switch to it
  }

  // ✅ 4. SWITCH CHAT Logic (Updated)
  selectSession(session: any) {
    // 🔥 FIX: Force the screen to switch back to 'chat' view
    this.switchView('chat'); 

    this.sessionId = session.id;
    this.chatHistory = []; // Clear screen immediately
    this.isLoading = true;

    // Fetch history from Backend
    this.aiService.getChatHistory(this.sessionId).subscribe({
      next: (history: any[]) => {
        this.chatHistory = history.map(msg => ({
          sender: msg.role === 'user' ? 'You' : 'AI Agent',
          text: msg.content
        }));
        this.isLoading = false;
        setTimeout(() => this.scrollToBottom(), 100);
      },
      error: (err: any) => { 
        console.error('Failed to load history', err);
        this.isLoading = false;
      }
    });
  }

  // ✅ 5. LOCAL STORAGE HELPERS
  saveSessionList() {
    localStorage.setItem('user_sessions_' + this.loginData.username, JSON.stringify(this.savedSessions));
  }

  loadSessionList() {
    const data = localStorage.getItem('user_sessions_' + this.loginData.username);
    if (data) {
      this.savedSessions = JSON.parse(data);
    }
  }

  // --- FILE UPLOAD ---
  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file) {
      this.isLoading = true;
      this.chatHistory.push({ sender: 'You', text: `📂 Uploading: ${file.name}...` });

      this.aiService.uploadFile(file).subscribe({
        next: (res: any) => {
          this.isLoading = false;
          this.chatHistory.push({ sender: 'AI Agent', text: res.reply });
          if (res.approval_required) {
            this.showApprovalButtons = true;
          }
        },
        error: (err) => {
          this.isLoading = false;
          this.chatHistory.push({ sender: 'System', text: '❌ Upload Failed.' });
          console.error(err);
        }
      });
    }
  }

  // --- AUTHENTICATION ---
  toggleAuthMode() {
    this.isLoginMode = !this.isLoginMode;
    this.loginData = { username: '', password: '' };
  }

  onAuthAction() {
    if (!this.loginData.username || !this.loginData.password) {
      alert('⚠️ Please enter both username and password');
      return;
    }

    if (this.isLoginMode) {
      this.aiService.login(this.loginData.username, this.loginData.password).subscribe({
        next: () => { 
          this.isAuthenticated = true; 
          this.initDashboard(); 
        },
        error: () => alert('❌ Invalid Credentials!')
      });
    } else {
      this.aiService.register(this.loginData.username, this.loginData.password).subscribe({
        next: () => { 
          alert('✅ Account Created! Please login.');
          this.isLoginMode = true; 
        },
        error: (err) => {
          if (err.status === 400) alert('⚠️ Username already exists.');
          else alert('❌ Registration failed. Try again.');
        }
      });
    }
  }

  onLogout() { 
    this.aiService.logout(); 
    this.isAuthenticated = false; 
    this.chatHistory = []; 
    this.savedSessions = []; // Clear sessions on logout
  }

  // --- CORE UI HELPERS ---
  formatText(text: string): SafeHtml {
    let formatted = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') 
      .replace(/\n/g, '<br>'); 
    return this.sanitizer.bypassSecurityTrustHtml(formatted);
  }

  ngAfterViewChecked() { this.scrollToBottom(); }
  scrollToBottom() { try { this.myScrollContainer.nativeElement.scrollTop = this.myScrollContainer.nativeElement.scrollHeight; } catch(err) { } }
  switchView(view: 'chat' | 'settings') { this.currentView = view; }

  // ✅ 6. SEND MESSAGE (Updated to use Session ID)
  sendMessage() {
    if (!this.userMessage.trim()) return;
    this.chatHistory.push({ sender: 'You', text: this.userMessage });
    const msg = this.userMessage;
    this.userMessage = ''; 
    this.isLoading = true; 
    this.showApprovalButtons = false;

    // Sending with Session ID
    this.aiService.sendMessage(msg, this.sessionId).subscribe({
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

  // --- EMPLOYEE & RISKS ---
  loadEmployees() { this.aiService.getEmployees().subscribe(data => this.employees = data); }

  addEmployee() {
    if (!this.newEmp.name || !this.newEmp.email) {
      alert('⚠️ Name and Email are required!');
      return;
    }

    const empData = {
      ...this.newEmp,
      skills: typeof this.newEmp.skills === 'string' 
        ? (this.newEmp.skills as string).split(',') 
        : this.newEmp.skills
    };

    this.aiService.addEmployee(
      empData.name, 
      empData.role, 
      empData.skills, 
      empData.email, 
      empData.rate
    ).subscribe({
      next: (res) => {
        alert(res.msg);
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