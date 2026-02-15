import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, tap, of } from 'rxjs'; // 👈 Added 'of'
import { delay } from 'rxjs/operators';     // 👈 Added 'delay'
import { environment } from '../environments/environment';

@Injectable({ providedIn: 'root' })
export class AiService {
  
  // 👇 TOGGLE THIS TO SWITCH MODES!
  // true  = Frontend Testing (No Backend needed)
  // false = Real Production (Connects to Python)
  private USE_MOCK = false; 

  private apiUrl = environment.apiUrl; 
  private tokenKey = 'nexus_token'; // renamed to avoid conflicts
  private isBrowser: boolean;

  constructor(private http: HttpClient, @Inject(PLATFORM_ID) platformId: Object) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  getDashboardData(): Observable<any> {
    if (this.USE_MOCK) {
      // Structure matches what your Python server returns
      return of({
        tasks_due: 5,
        overdue: 2,
        active_agents: 11,
        resolved_risks: 15,
        line_chart: {
          labels: ['01 Feb', '03 Feb', '05 Feb', '07 Feb', '09 Feb', '11 Feb'],
          datasets: [{
            label: 'Tasks Due',
            data: [2, 5, 3, 8, 4, 6],
            borderColor: '#6C5DD3',
            backgroundColor: 'transparent'
          }]
        },
        donut_chart: {
          labels: ['Completed', 'In Progress', 'Not Started'],
          datasets: [{
            data: [15, 10, 5],
            backgroundColor: ['#6C5DD3', '#3F8CFF', '#FFCE73']
          }]
        },
        finance_table: [
          { date: 'Feb 12', category: 'Software', details: 'Subscription', amount: '-$50.00', status: 'Completed', isPositive: false }
        ]
      }).pipe(delay(500));
    }

    // 🔗 REAL MODE: Hits your Python server which fetches from Trello/n8n
    return this.http.get<any>(`${this.apiUrl}/dashboard/data`, this.getAuthOptions());
  }
  
  // --- AUTHENTICATION ---
  login(username: string, password: string): Observable<any> {
    // 1. MOCK MODE
    if (this.USE_MOCK) {
      console.log(`[Mock] Logging in user: ${username}`);
      return new Observable(observer => {
        setTimeout(() => {
          if (this.isBrowser) {
            localStorage.setItem(this.tokenKey, 'fake-jwt-token-999');
            localStorage.setItem('current_user', username);
          }
          observer.next({ access_token: 'fake-jwt-token-999' });
          observer.complete();
        }, 800);
      });
    }

    // 2. REAL BACKEND MODE
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    return this.http.post<any>(`${this.apiUrl}/token`, formData).pipe(
      tap(res => {
        if (this.isBrowser) {
          localStorage.setItem(this.tokenKey, res.access_token);
          localStorage.setItem('current_user', username); 
        }
      })
    );
  }

  deleteEmployee(email: string): Observable<any> {
  return this.http.delete(`${this.apiUrl}/employees/${email}`, this.getAuthOptions());
}

updateEmployee(email: string, data: any): Observable<any> {
  return this.http.put(`${this.apiUrl}/employees/${email}`, data, this.getAuthOptions());
}


  register(username: string, password: string): Observable<any> {
    if (this.USE_MOCK) return this.login(username, password); // Just log in directly for mock
    return this.http.post(`${this.apiUrl}/register`, { username, password });
  }

  logout() {
    if (this.isBrowser) {
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem('current_user');
    }
  }

  isLoggedIn(): boolean {
    if (!this.isBrowser) return false;
    return !!localStorage.getItem(this.tokenKey);
  }

  // --- CHAT & CORE FEATURES ---

  sendMessage(userMessage: string, sessionId: string): Observable<any> {
    if (this.USE_MOCK) {
      return of({ 
        reply: `[Mock AI] I received: "${userMessage}". I can't think yet, but the UI works!`, 
        approval_required: false 
      }).pipe(delay(1000));
    }
    return this.http.post<any>(`${this.apiUrl}/chat`, { message: userMessage, session_id: sessionId }, this.getAuthOptions());
  }

  getChatHistory(sessionId: string): Observable<any[]> {
    if (this.USE_MOCK) {
      return of([
        { role: 'system', content: 'Welcome. This is a Mock History session.' },
        { role: 'assistant', content: 'How can I help you manage your project today?' }
      ]).pipe(delay(500));
    }
    return this.http.get<any[]>(`${this.apiUrl}/chat/history/${sessionId}`, this.getAuthOptions());
  }

  uploadFile(file: File): Observable<any> {
    if (this.USE_MOCK) {
      return of({ reply: `File "${file.name}" uploaded (Mock Mode).`, approval_required: true }).pipe(delay(1500));
    }
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.apiUrl}/upload`, formData, this.getAuthOptions());
  }

  // --- DASHBOARD & TEAM ---
  // src/app/ai.service.ts

getProfile(): Observable<any> {
  return this.http.get<any>(`${this.apiUrl}/user/profile`, this.getAuthOptions()); // 👈 Ensure this helper is here
}

updateProfile(data: any): Observable<any> {
  return this.http.post<any>(`${this.apiUrl}/user/profile`, data, this.getAuthOptions()); // 👈 And here
}

  getRisks(): Observable<any> { 
    if (this.USE_MOCK) {
      return of({ risks: ['Budget Overrun > 10%', 'Server Latency High', 'Compliance Audit Pending'] }).pipe(delay(600));
    }
    return this.http.get<any>(`${this.apiUrl}/risks`, this.getAuthOptions()); 
  }

  getEmployees(): Observable<any[]> { 
    if (this.USE_MOCK) {
      return of([
        { name: 'Sarah Connor', role: 'Product Owner', skills: ['Agile', 'Jira'], email: 'sarah@nexus.com', rate: 85 },
        { name: 'John Doe', role: 'Lead Dev', skills: ['Angular', 'Python'], email: 'john@nexus.com', rate: 95 }
      ]).pipe(delay(400));
    }
    return this.http.get<any[]>(`${this.apiUrl}/employees`, this.getAuthOptions()); 
  }
  
  addEmployee(name: string, role: string, skills: string[], email: string, rate: number): Observable<any> {
    if (this.USE_MOCK) return of({ msg: 'User Added (Mock)' }).pipe(delay(500));
    return this.http.post<any>(`${this.apiUrl}/employees`, { name, role, skills, email, rate }, this.getAuthOptions());
  }

  // --- APPROVALS ---

  approvePlan(sessionId: string): Observable<any> { 
    if (this.USE_MOCK) return of({}).pipe(delay(500));
    return this.http.post<any>(`${this.apiUrl}/approve`, { session_id: sessionId }, this.getAuthOptions()); 
  }
  
  rejectPlan(sessionId: string, reasonText: string = 'User rejected the plan.'): Observable<any> {
  return this.http.post<any>(`${this.apiUrl}/reject`, { 
    session_id: sessionId, 
    reason: reasonText 
  }, this.getAuthOptions());
}

  // --- HELPER ---
  private getAuthOptions() {
    if (!this.isBrowser) return {};
    const token = localStorage.getItem(this.tokenKey);
    return {
      headers: new HttpHeaders({
        'Authorization': `Bearer ${token}`
      })
    };
  }
}