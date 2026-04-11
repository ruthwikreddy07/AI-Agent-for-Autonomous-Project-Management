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
  step = 1; // 1: Core Details, 2: AI Context
  
  // Payload Fields
  username = '';
  password = '';
  full_name = '';
  profession = 'Software Engineer';
  project_focus = 'Software Development';

  constructor(private aiService: AiService) {}

  nextStep() {
    if (!this.username || !this.password || !this.full_name) {
      alert("Please fill out all required fields first.");
      return;
    }
    this.step = 2;
  }

  prevStep() {
    this.step = 1;
  }

  toggleMode() {
    this.isLogin = !this.isLogin;
    this.step = 1;
  }

  onSubmit() {
    if (this.isLogin) {
      if (!this.username || !this.password) return;
      this.aiService.login(this.username, this.password).subscribe({
        next: () => {
          this.loginSuccess.emit();
        },
        error: () => alert('Invalid Credentials')
      });
    } else {
      // Registration complete payload
      const payload = {
        username: this.username,
        password: this.password,
        full_name: this.full_name,
        email: this.username, // Using username as email conceptually
        profession: this.profession,
        project_focus: this.project_focus
      };

      this.aiService.register(payload).subscribe({
        next: () => {
          alert('Workspace Set Up Successfully! Please log in.');
          this.toggleMode();
        },
        error: () => alert('Username exists. Please try another.')
      });
    }
  }
}