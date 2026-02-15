import { Component, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService } from '../ai.service'; // 👈 Adjust the path if necessary
import { Router } from '@angular/router';
@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './settings.html',
  styleUrls: ['./settings.css']
})
export class SettingsComponent implements OnInit {
  @Output() goBack = new EventEmitter<void>();
  
  
  username = '';
  displayName = ''; // 🚀 New: Bound to input
  email = '';       // 🚀 New: Bound to input
  isDarkMode = false;
  links = { trello: '', n8n: '', slack: '' };

  constructor(private aiService: AiService) {}

  triggerBack() {
    this.goBack.emit(); // 🚀 Signal to app.ts
  }
  ngOnInit() {
    this.username = localStorage.getItem('current_user') || 'User';
    
    // 1. Load profile data from Backend on startup
    this.aiService.getProfile().subscribe({
      next: (data: any) => {
        this.displayName = data.display_name;
        this.email = data.email;
      },
      error: (err: any) => console.error('Could not load profile', err)
    });

    const saved = localStorage.getItem('nexus_links');
    if (saved) { this.links = JSON.parse(saved); }
    this.isDarkMode = document.body.classList.contains('dark-theme');
  }

  saveSettings() {
    // 2. Prepare the data for the backend
    const profileData = { 
      display_name: this.displayName, 
      email: this.email 
    };

    // 3. Save to MongoDB via the Backend
    this.aiService.updateProfile(profileData).subscribe({
      next: () => {
        // Also save your links locally
        localStorage.setItem('nexus_links', JSON.stringify(this.links));
        alert('✅ Profile and Settings Saved Successfully!');
      },
      error: (err: any) => alert('❌ Error saving profile to database')
    });
  }

  toggleDarkMode() {
    this.isDarkMode = !this.isDarkMode;
    document.body.classList.toggle('dark-theme', this.isDarkMode);
  }
}