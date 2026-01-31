import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable({ providedIn: 'root' })
export class AiService {
  private apiUrl = environment.apiUrl; // e.g. http://127.0.0.1:8000
  private tokenKey = 'auth_token';
  private isBrowser: boolean;

  constructor(private http: HttpClient, @Inject(PLATFORM_ID) platformId: Object) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  // --- AUTH ---
  login(username: string, password: string): Observable<any> {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    return this.http.post<any>(`${this.apiUrl}/token`, formData).pipe(
      tap(res => {
        if (this.isBrowser) {
          localStorage.setItem(this.tokenKey, res.access_token);
          // ✅ ADD THIS: Save username so we don't lose it on refresh
          localStorage.setItem('current_user', username); 
        }
      })
    );
  }

  logout() {
    if (this.isBrowser) {
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem('current_user'); // ✅ Clean up
    }
  }

  isLoggedIn(): boolean {
    if (!this.isBrowser) return false;
    return !!localStorage.getItem(this.tokenKey);
  }

  register(username: string, password: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/register`, { username, password });
  }

  // --- CORE FEATURES ---

  sendMessage(userMessage: string, sessionId: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/chat`, { 
      message: userMessage, 
      session_id: sessionId 
    }, this.getAuthOptions());
  }

  // ✅ UPDATE 2: Added this missing function
  getChatHistory(sessionId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/chat/history/${sessionId}`, this.getAuthOptions());
  }

  // ✅ NEW: Upload Method
  uploadFile(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    // Angular automatically sets Content-Type to multipart/form-data
    return this.http.post<any>(`${this.apiUrl}/upload`, formData, this.getAuthOptions());
  }

  getRisks(): Observable<any> { return this.http.get<any>(`${this.apiUrl}/risks`, this.getAuthOptions()); }
  
  approvePlan(): Observable<any> { return this.http.post<any>(`${this.apiUrl}/approve`, {}, this.getAuthOptions()); }
  
  rejectPlan(): Observable<any> { return this.http.post<any>(`${this.apiUrl}/reject`, {}, this.getAuthOptions()); }

  getEmployees(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/employees`, this.getAuthOptions()); }
  
  addEmployee(name: string, role: string, skills: string[], email: string, rate: number): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/employees`, { name, role, skills, email, rate }, this.getAuthOptions());
  }

  // Helper for Headers
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