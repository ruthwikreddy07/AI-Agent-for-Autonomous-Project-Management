import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../environments/environment';

@Injectable({ providedIn: 'root' })
export class AiService {
  private apiUrl = environment.apiUrl;
  private tokenKey = 'auth_token';
  private isBrowser: boolean;

  constructor(private http: HttpClient, @Inject(PLATFORM_ID) platformId: Object) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  login(username: string, password: string): Observable<any> {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    return this.http.post<any>(`${this.apiUrl}/token`, formData).pipe(
      tap(res => {
        if (this.isBrowser) {
          localStorage.setItem(this.tokenKey, res.access_token);
        }
      })
    );
  }

  logout() {
    if (this.isBrowser) {
      localStorage.removeItem(this.tokenKey);
    }
  }

  isLoggedIn(): boolean {
    if (!this.isBrowser) {
      return false;
    }
    return !!localStorage.getItem(this.tokenKey);
  }

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