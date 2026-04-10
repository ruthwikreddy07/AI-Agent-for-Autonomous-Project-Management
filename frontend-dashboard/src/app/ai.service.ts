import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, tap, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { environment } from '../environments/environment';

@Injectable({ providedIn: 'root' })
export class AiService {
  
  // 👇 TOGGLE THIS TO SWITCH MODES!
  private USE_MOCK = false; 

  private apiUrl = environment.apiUrl; 
  private tokenKey = 'nexus_token';
  private isBrowser: boolean;

  constructor(private http: HttpClient, @Inject(PLATFORM_ID) platformId: Object) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  getDashboardData(): Observable<any> {
    if (this.USE_MOCK) {
      return of({
        tasks_due: 5, overdue: 2, active_agents: 11, resolved_risks: 15,
        user_role: 'admin',
        line_chart: {
          labels: ['01 Feb', '03 Feb', '05 Feb', '07 Feb', '09 Feb', '11 Feb'],
          datasets: [{ label: 'Tasks Due', data: [2, 5, 3, 8, 4, 6], borderColor: '#6C5DD3', backgroundColor: 'transparent' }]
        },
        donut_chart: {
          labels: ['Completed', 'In Progress', 'Not Started'],
          datasets: [{ data: [15, 10, 5], backgroundColor: ['#6C5DD3', '#3F8CFF', '#FFCE73'] }]
        },
        finance_table: [
          { date: 'Feb 12', category: 'Software', details: 'Subscription', amount: '-$50.00', status: 'Completed', isPositive: false }
        ]
      }).pipe(delay(500));
    }
    return this.http.get<any>(`${this.apiUrl}/dashboard/data`, this.getAuthOptions());
  }
  
  // ==========================================
  // 🔐 AUTHENTICATION
  // ==========================================
  login(username: string, password: string): Observable<any> {
    if (this.USE_MOCK) {
      return new Observable(observer => {
        setTimeout(() => {
          if (this.isBrowser) {
            localStorage.setItem(this.tokenKey, 'fake-jwt-token-999');
            localStorage.setItem('current_user', username);
            localStorage.setItem('user_role', 'admin');
          }
          observer.next({ access_token: 'fake-jwt-token-999', role: 'admin' });
          observer.complete();
        }, 800);
      });
    }

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    return this.http.post<any>(`${this.apiUrl}/token`, formData).pipe(
      tap(res => {
        if (this.isBrowser) {
          localStorage.setItem(this.tokenKey, res.access_token);
          localStorage.setItem('current_user', username);
          localStorage.setItem('user_role', res.role || 'developer');
        }
      })
    );
  }

  register(username: string, password: string): Observable<any> {
    if (this.USE_MOCK) return this.login(username, password);
    return this.http.post(`${this.apiUrl}/register`, { username, password });
  }

  logout() {
    if (this.isBrowser) {
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem('current_user');
      localStorage.removeItem('user_role');
    }
  }

  isLoggedIn(): boolean {
    if (!this.isBrowser) return false;
    return !!localStorage.getItem(this.tokenKey);
  }

  // ==========================================
  // 🔐 RBAC — ROLE MANAGEMENT
  // ==========================================
  getRole(): string {
    if (!this.isBrowser) return 'developer';
    return localStorage.getItem('user_role') || 'developer';
  }

  isPM(): boolean {
    const role = this.getRole();
    return role === 'pm' || role === 'admin';
  }

  isAdmin(): boolean {
    return this.getRole() === 'admin';
  }

  getUserRole(): Observable<any> {
    if (this.USE_MOCK) return of({ role: 'admin' }).pipe(delay(200));
    return this.http.get<any>(`${this.apiUrl}/user/role`, this.getAuthOptions());
  }

  // ==========================================
  // 💬 CHAT & CORE FEATURES
  // ==========================================
  sendMessage(userMessage: string, sessionId: string): Observable<any> {
    if (this.USE_MOCK) {
      return of({ reply: `[Mock AI] I received: "${userMessage}".`, approval_required: false }).pipe(delay(1000));
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

  // ==========================================
  // 👥 TEAM & PROFILE
  // ==========================================
  getProfile(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/user/profile`, this.getAuthOptions());
  }

  updateProfile(data: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/user/profile`, data, this.getAuthOptions());
  }

  getRisks(): Observable<any> { 
    if (this.USE_MOCK) return of({ risks: ['Budget Overrun > 10%'] }).pipe(delay(600));
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

  deleteEmployee(email: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/employees/${email}`, this.getAuthOptions());
  }

  updateEmployee(email: string, data: any): Observable<any> {
    return this.http.put(`${this.apiUrl}/employees/${email}`, data, this.getAuthOptions());
  }

  // ==========================================
  // ✅ APPROVALS
  // ==========================================
  approvePlan(sessionId: string): Observable<any> { 
    if (this.USE_MOCK) return of({}).pipe(delay(500));
    return this.http.post<any>(`${this.apiUrl}/approve`, { session_id: sessionId }, this.getAuthOptions()); 
  }
  
  rejectPlan(sessionId: string, reasonText: string = 'User rejected the plan.'): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/reject`, { session_id: sessionId, reason: reasonText }, this.getAuthOptions());
  }

  // ==========================================
  // 📁 PROJECTS
  // ==========================================
  getProjects(): Observable<any[]> {
    if (this.USE_MOCK) return of([]).pipe(delay(300));
    return this.http.get<any[]>(`${this.apiUrl}/projects`, this.getAuthOptions());
  }

  createProject(project: any): Observable<any> {
    if (this.USE_MOCK) return of({ msg: 'Created (Mock)' }).pipe(delay(300));
    return this.http.post<any>(`${this.apiUrl}/projects`, project, this.getAuthOptions());
  }

  deleteProject(projectName: string): Observable<any> {
    if (this.USE_MOCK) return of({ msg: 'Deleted (Mock)' }).pipe(delay(300));
    return this.http.delete<any>(`${this.apiUrl}/projects/${projectName}`, this.getAuthOptions());
  }

  // ==========================================
  // ⏱ TIME TRACKING
  // ==========================================
  logTime(taskName: string, hours: number, note: string = ''): Observable<any> {
    if (this.USE_MOCK) return of({ msg: 'Logged (Mock)' }).pipe(delay(300));
    return this.http.post<any>(`${this.apiUrl}/time-log`, { task_name: taskName, hours, note }, this.getAuthOptions());
  }

  getTimeLogs(taskName: string): Observable<any> {
    if (this.USE_MOCK) return of({ total_hours: 0, entries: [] }).pipe(delay(300));
    return this.http.get<any>(`${this.apiUrl}/time-log/${taskName}`, this.getAuthOptions());
  }

  // ==========================================
  // 🏃 SPRINT MANAGEMENT
  // ==========================================
  getSprints(projectId: string = 'default'): Observable<any[]> {
    if (this.USE_MOCK) return of([]).pipe(delay(300));
    return this.http.get<any[]>(`${this.apiUrl}/sprints?project_id=${projectId}`, this.getAuthOptions());
  }

  createSprint(sprint: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/sprints`, sprint, this.getAuthOptions());
  }

  updateSprint(sprintId: string, sprint: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/sprints/${sprintId}`, sprint, this.getAuthOptions());
  }

  getSprintBurndown(sprintId: string): Observable<any> {
    if (this.USE_MOCK) return of({ labels: [], ideal: [], actual: [] }).pipe(delay(300));
    return this.http.get<any>(`${this.apiUrl}/sprints/${sprintId}/burndown`, this.getAuthOptions());
  }

  // ==========================================
  // 📦 EPIC → STORY → TASK HIERARCHY
  // ==========================================
  getEpics(): Observable<any[]> {
    if (this.USE_MOCK) return of([]).pipe(delay(300));
    return this.http.get<any[]>(`${this.apiUrl}/epics`, this.getAuthOptions());
  }

  createEpic(epic: any): Observable<any> {
    if (this.USE_MOCK) return of({ msg: 'Created', id: 'mock-epic-1' }).pipe(delay(300));
    return this.http.post<any>(`${this.apiUrl}/epics`, epic, this.getAuthOptions());
  }

  updateEpic(epicId: string, data: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/epics/${epicId}`, data, this.getAuthOptions());
  }

  deleteEpic(epicId: string): Observable<any> {
    return this.http.delete<any>(`${this.apiUrl}/epics/${epicId}`, this.getAuthOptions());
  }

  getStories(epicId?: string): Observable<any[]> {
    if (this.USE_MOCK) return of([]).pipe(delay(300));
    const url = epicId ? `${this.apiUrl}/stories?epic_id=${epicId}` : `${this.apiUrl}/stories`;
    return this.http.get<any[]>(url, this.getAuthOptions());
  }

  createStory(story: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/stories`, story, this.getAuthOptions());
  }

  getTasks(storyId?: string, epicId?: string): Observable<any[]> {
    if (this.USE_MOCK) return of([]).pipe(delay(300));
    let url = `${this.apiUrl}/tasks`;
    const params: string[] = [];
    if (storyId) params.push(`story_id=${storyId}`);
    if (epicId) params.push(`epic_id=${epicId}`);
    if (params.length) url += '?' + params.join('&');
    return this.http.get<any[]>(url, this.getAuthOptions());
  }

  createTask(task: any): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/tasks`, task, this.getAuthOptions());
  }

  updateTask(taskId: string, data: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/tasks/${taskId}`, data, this.getAuthOptions());
  }

  getWorkBreakdown(): Observable<any[]> {
    if (this.USE_MOCK) return of([]).pipe(delay(300));
    return this.http.get<any[]>(`${this.apiUrl}/work-breakdown`, this.getAuthOptions());
  }

  // ==========================================
  // 🎙️ MEETINGS & PRE-MORTEM AI (SPRINT 3)
  // ==========================================
  
  getMeetings(): Observable<any[]> {
    if (this.USE_MOCK) return of([]).pipe(delay(300));
    return this.http.get<any[]>(`${this.apiUrl}/meetings`, this.getAuthOptions());
  }

  getMeeting(id: string): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/meetings/${id}`, this.getAuthOptions());
  }

  getRiskRegister(projectId: string = 'default'): Observable<any[]> {
    if (this.USE_MOCK) return of([]).pipe(delay(300));
    return this.http.get<any[]>(`${this.apiUrl}/risk-register?project_id=${projectId}`, this.getAuthOptions());
  }

  updateRisk(id: string, data: any): Observable<any> {
    return this.http.put<any>(`${this.apiUrl}/risk-register/${id}`, data, this.getAuthOptions());
  }

  getSprintScopeHealth(sprintId: string): Observable<any> {
    if (this.USE_MOCK) return of({ capacity: 0, assigned: 0, utilization_pct: 0, is_overloaded: false, defer_suggestions: [] }).pipe(delay(300));
    return this.http.get<any>(`${this.apiUrl}/sprints/${sprintId}/scope-health`, this.getAuthOptions());
  }

  predictRisks(): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/chat`, { message: "predict risks" }, this.getAuthOptions());
  }

  // ==========================================
  // 📊 GANTT CHART
  // ==========================================
  getGanttData(): Observable<any> {
    if (this.USE_MOCK) return of({ tasks: [], total: 0 }).pipe(delay(300));
    return this.http.get<any>(`${this.apiUrl}/gantt-data`, this.getAuthOptions());
  }

  // ==========================================
  // 🔧 HELPER
  // ==========================================
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