import { Component, OnInit, AfterViewChecked, ViewChild, ElementRef, Output, EventEmitter } from '@angular/core';import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService } from '../ai.service'; // 👈 FIXED PATH
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { HttpClient } from '@angular/common/http'; 
import { Router } from '@angular/router';
import { NgZone } from '@angular/core'; // 🚀 Add this

const isSameDay = (d1: Date, d2: Date) => {
  return d1.getFullYear() === d2.getFullYear() && d1.getMonth() === d2.getMonth() && d1.getDate() === d2.getDate();
};

@Component({
  selector: 'app-chat', // 👈 FIXED SELECTOR
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.html',
  styleUrls: ['./chat.css']
})
export class ChatComponent implements OnInit, AfterViewChecked { // 👈 FIXED CLASS NAME
  @ViewChild('scrollMe') private myScrollContainer!: ElementRef;
  @Output() navigate = new EventEmitter<string>();
  isAuthenticated: boolean = false;
  isLoginMode: boolean = true;
  
  sessionId: string = ''; 
  savedSessions: { id: string, label: string }[] = []; 
  groupedSessions: { label: string, sessions: any[] }[] = []; 

  currentView: 'chat' | 'settings' = 'chat';
  userMessage: string = '';
  // src/app/chat/chat.ts (Around line 29)
chatHistory: { sender: string, text: string, html?: SafeHtml }[] = [];
  realRisks: string[] = [];
  employees: any[] = [];
  
  loginData = { username: '', password: '' };
  newEmp = { name: '', role: '', skills: '', email: '', rate: 50 };
  
  isLoading: boolean = false;
  showApprovalButtons: boolean = false;

  constructor(
    private aiService: AiService, 
    private sanitizer: DomSanitizer,
    private http: HttpClient,
    private router: Router,
    private ngZone: NgZone
  ) {}

  ngOnInit() {
    this.isAuthenticated = this.aiService.isLoggedIn();
    const storedUser = localStorage.getItem('current_user');
    if (storedUser) { this.loginData.username = storedUser; }
    if (this.isAuthenticated) this.initDashboard();
  }

  initDashboard() {
  this.isLoading = true; // 🚀 Start loading
  this.loadSessionList();
  
  if (this.savedSessions.length === 0) {
    this.startNewChat();
    this.isLoading = false; // New chats are instant
  } else {
    this.selectSession(this.savedSessions[0]);
  }
  this.loadEmployees();
  // 🚀 FETCH RISKS SEPARATELY (Don't let it block the chat)
  this.aiService.getRisks().subscribe({
    next: (res: any) => this.realRisks = res.risks,
    error: () => console.log("Risks failed, but chat will still open.")
  });
}

  startNewChat() {
    const timestamp = new Date().getTime();
    const newId = `session-${this.loginData.username}-${timestamp}`;
    const newSession = { id: newId, label: `Chat ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}` };
    this.savedSessions.unshift(newSession);
    this.saveSessionList(); 
    this.selectSession(newSession); 
  }

  // src/app/chat/chat.ts
selectSession(session: any) {
  this.sessionId = session.id;
  this.chatHistory = []; 
  this.isLoading = true;
  this.lastMessageCount = 0;

  this.aiService.getChatHistory(this.sessionId).subscribe({
    next: (history: any[]) => {
      // 🚀 THE FIX: Map history and format HTML ONCE
      this.chatHistory = history.map(msg => {
        const sender = msg.role === 'user' ? 'You' : 'AI Agent';
        return { 
          sender, 
          text: msg.content, 
          html: sender === 'AI Agent' ? this.formatText(msg.content) : undefined 
        };
      });
      
      this.isLoading = false;
      setTimeout(() => this.scrollToBottom(), 100);
    },
    error: (err: any) => {
      console.error('Failed to load history', err);
      this.isLoading = false;
    }
  });
}

  saveSessionList() {
    localStorage.setItem('user_sessions_' + this.loginData.username, JSON.stringify(this.savedSessions));
    this.groupSessions();
  }

  loadSessionList() {
    const data = localStorage.getItem('user_sessions_' + this.loginData.username);
    if (data) { this.savedSessions = JSON.parse(data); }
    this.groupSessions(); 
  }

  groupSessions() {
    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);
    const groups: { [key: string]: any[] } = { "Today": [], "Yesterday": [] };

    this.savedSessions.sort((a: any, b: any) => {
      const timeA = parseInt(a.id.split('-').pop() || '0');
      const timeB = parseInt(b.id.split('-').pop() || '0');
      return timeB - timeA;
    });

    this.savedSessions.forEach(session => {
      const timestamp = parseInt(session.id.split('-').pop() || '0');
      const date = new Date(timestamp);
      if (isSameDay(date, today)) { groups["Today"].push(session); } 
      else if (isSameDay(date, yesterday)) { groups["Yesterday"].push(session); } 
      else {
        const dateKey = date.toLocaleDateString('en-GB'); 
        if (!groups[dateKey]) groups[dateKey] = [];
        groups[dateKey].push(session);
      }
    });

    this.groupedSessions = Object.keys(groups).filter(key => groups[key].length > 0).map(key => ({ label: key, sessions: groups[key] }));
  }

  deleteSession(event: Event, sessionId: string) {
    event.stopPropagation(); 
    if(!confirm("Delete this chat history?")) return;
    this.savedSessions = this.savedSessions.filter(s => s.id !== sessionId);
    this.saveSessionList(); 
    const apiUrl = (this.aiService as any)['apiUrl']; // 👈 FIXED OVERRIDE
    this.http.delete(`${apiUrl}/chat/history/${sessionId}`).subscribe();
    if (this.sessionId === sessionId) {
      if (this.savedSessions.length > 0) { this.selectSession(this.savedSessions[0]); } 
      else { this.startNewChat(); }
    }
  }

  onFileSelected(event: any) {
    const file: File = event.target.files[0];
    if (file) {
      this.isLoading = true;
      this.chatHistory.push({ sender: 'You', text: `📂 Uploading: ${file.name}...` });
      this.aiService.uploadFile(file).subscribe({
        // Inside onFileSelected() next block
next: (res: any) => { 
  this.isLoading = false;
  this.chatHistory.push({ 
    sender: 'AI Agent', 
    text: res.reply,
    html: this.formatText(res.reply) // 🚀 Add this here too
  });
  if (res.approval_required) { this.showApprovalButtons = true; }
},
        error: (err: any) => { 
          this.isLoading = false;
          this.chatHistory.push({ sender: 'System', text: '❌ Upload Failed.' });
        }
      });
    }
  }

  toggleAuthMode() { this.isLoginMode = !this.isLoginMode; this.loginData = { username: '', password: '' }; }

  onAuthAction() {
    if (!this.loginData.username || !this.loginData.password) return;
    if (this.isLoginMode) {
      this.aiService.login(this.loginData.username, this.loginData.password).subscribe({
        next: () => { this.isAuthenticated = true; this.initDashboard(); },
        error: () => alert('❌ Invalid Credentials!')
      });
    } else {
      this.aiService.register(this.loginData.username, this.loginData.password).subscribe({
        next: () => { alert('✅ Account Created!'); this.isLoginMode = true; },
        error: (err: any) => { if (err.status === 400) alert('⚠️ Username already exists.'); } 
      });
    }
  }

onLogout() { 
    this.aiService.logout(); 
    this.isAuthenticated = false; 
    this.chatHistory = []; 
    this.savedSessions = [];
    this.router.navigate(['/login']); // 🚀 Physically sends user back to login
  }
  formatText(text: string): SafeHtml {
    let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>'); 
    return this.sanitizer.bypassSecurityTrustHtml(formatted);
  }

  // 1. Add this variable at the top of your class (near sessionId)
private lastMessageCount = 0;

// 2. Update your scroll logic to this:
ngAfterViewChecked() {
  // Only scroll if the number of messages has actually increased
  if (this.chatHistory.length > this.lastMessageCount) {
    this.scrollToBottom();
    this.lastMessageCount = this.chatHistory.length;
  }
}
  
  scrollToBottom() { try { this.myScrollContainer.nativeElement.scrollTop = this.myScrollContainer.nativeElement.scrollHeight; } catch(err) { } }
  goBack() {
  this.ngZone.run(() => {
    this.router.navigate(['/dashboard']);
  });
}
  switchView(view: 'chat' | 'settings') { this.currentView = view; }

  sendMessage() {
    if (!this.userMessage.trim()) return;
    this.chatHistory.push({ sender: 'You', text: this.userMessage });
    const msg = this.userMessage;
    this.userMessage = ''; this.isLoading = true; this.showApprovalButtons = false;

    this.aiService.sendMessage(msg, this.sessionId).subscribe({
      // Inside sendMessage() next block
next: (res: any) => { 
  this.chatHistory.push({ 
    sender: 'AI Agent', 
    text: res.reply, 
    html: this.formatText(res.reply) // 🚀 Format here
  });
  this.isLoading = false;
  if (res.approval_required) this.showApprovalButtons = true;
  this.fetchRisks();
},
      error: () => { 
        this.chatHistory.push({ sender: 'System', text: '⚠️ Connection Error.' }); 
        this.isLoading = false; 
      }
    });
  }

// src/app/chat/chat.ts

loadEmployees() { 
  this.aiService.getEmployees().subscribe({
    next: (data: any) => {
      // 🚀 THE FIX: Check if data is already an array or wrapped in an object
      if (Array.isArray(data)) {
        this.employees = data;
      } else if (data && data.employees) {
        this.employees = data.employees;
      } else {
        this.employees = []; // Fallback to empty array
      }
      
      console.log('Successfully loaded members:', this.employees.length);
    },
    error: (err: any) => {
      console.error('Failed to load team roster', err);
      this.employees = []; // Prevent UI crashes
    }
  }); 
}
  addEmployee() {
    if (!this.newEmp.name || !this.newEmp.email) return;
    const empData = { ...this.newEmp, skills: typeof this.newEmp.skills === 'string' ? (this.newEmp.skills as string).split(',') : this.newEmp.skills };
    this.aiService.addEmployee(empData.name, empData.role, empData.skills, empData.email, empData.rate).subscribe({
      next: (res: any) => { alert(res.msg); this.newEmp = { name: '', role: '', skills: '', email: '', rate: 50 }; this.loadEmployees(); }, 
      error: () => alert('Error adding employee')
    });
  }

  fetchRisks() { this.aiService.getRisks().subscribe((res: any) => this.realRisks = res.risks); } 
  
  // src/app/chat/chat.ts

onApprove() {
  // 🚀 THE FIX: Define the ID from your current session
  const currentId = this.sessionId; 
  
  if (!currentId) {
    console.error("No active session ID found!");
    return;
  }

  this.showApprovalButtons = false; 
  this.isLoading = true;

  this.aiService.approvePlan(currentId).subscribe({
    next: (res: any) => {
      // 🚀 Push the actual professional message to the UI
      this.chatHistory.push({ 
        sender: 'AI Agent', 
        text: res.reply,
        html: this.formatText(res.reply) 
      });
      
      this.isLoading = false;
      this.fetchRisks();
      setTimeout(() => this.scrollToBottom(), 100);
    },
    error: (err) => {
      console.error("Approval failed", err);
      this.isLoading = false;
    }
  });
}
  
  onReject() {
  const currentId = this.sessionId;
  this.showApprovalButtons = false;

  this.aiService.rejectPlan(currentId).subscribe({
    next: (res: any) => {
      // This "pushes" the message into your chat window instantly
      this.chatHistory.push({ 
        sender: 'AI Agent', 
        text: res.reply,
        html: this.formatText(res.reply) 
      });
      this.isLoading = false;
    }
  });
}
}