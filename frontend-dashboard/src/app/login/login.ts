import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService } from '../ai.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class LoginComponent {
  @Output() loginSuccess = new EventEmitter<void>(); // 🚀 Re-add the emitter
  
  isLogin = true;
  username = '';
  password = '';

constructor(private aiService: AiService) {}
  onSubmit() {
    if (!this.username || !this.password) return;

    if (this.isLogin) {
      this.aiService.login(this.username, this.password).subscribe({
        next: () => {
          this.loginSuccess.emit(); // 🚀 Tell parent to swap to dashboard
        },
        error: () => alert('Invalid Credentials')
      });
    } else {
      this.aiService.register(this.username, this.password).subscribe({
        next: () => {
          alert('Account created! Please log in.');
          this.isLogin = true;
        },
        error: () => alert('Username exists')
      });
    }
  }
}