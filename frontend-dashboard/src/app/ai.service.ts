import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AiService {
  private apiUrl = 'http://127.0.0.1:8000';
  private tokenKey = 'auth_token';

  constructor(private http: HttpClient) { }

  login(username: string, password: string): Observable<any> {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    return this.http.post<any>(`${this.apiUrl}/token`, formData).pipe(
      tap(res => localStorage.setItem(this.tokenKey, res.access_token))
    );
  }

  logout() { localStorage.removeItem(this.tokenKey); }
  isLoggedIn(): boolean { return !!localStorage.getItem(this.tokenKey); }

  sendMessage(userMessage: string): Observable<any> {
    return this.http.post<any>(`${this.apiUrl}/chat`, { message: userMessage });
  }

  getRisks(): Observable<any> { return this.http.get<any>(`${this.apiUrl}/risks`); }
  approvePlan(): Observable<any> { return this.http.post<any>(`${this.apiUrl}/approve`, {}); }
  rejectPlan(): Observable<any> { return this.http.post<any>(`${this.apiUrl}/reject`, {}); }

  getEmployees(): Observable<any[]> { return this.http.get<any[]>(`${this.apiUrl}/employees`); }
  
  // UPDATED: Accepts EMAIL
  addEmployee(name: string, role: string, skills: string, email: string): Observable<any> {
    const skillList = skills.split(',').map(s => s.trim());
    return this.http.post<any>(`${this.apiUrl}/employees`, { name, role, skills: skillList, email });
  }
}