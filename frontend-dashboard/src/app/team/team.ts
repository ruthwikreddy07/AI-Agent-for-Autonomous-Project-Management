import { Component, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService } from '../ai.service';
import { Router } from '@angular/router';
import { NgZone } from '@angular/core'; // 🚀 Add this

@Component({
  selector: 'app-team',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './team.html',
  styleUrls: ['./team.css']
})
export class TeamComponent implements OnInit {
  @Output() goBack = new EventEmitter<void>();
  constructor(private aiService: AiService, private router: Router,private ngZone: NgZone ) {}
  
  
  employees: any[] = [];
  teamHealth: any[] = [];
  commitStats: any = {};
  showModal = false;
  isEditing = false;
  newEmp = { name: '', role: '', skills: '', email: '', rate: 50 };

  ngOnInit() { 
    this.loadEmployees(); 
    this.loadTeamHealth();
    this.loadCommitStats();
  }

  loadTeamHealth() {
    this.aiService.getTeamHealth().subscribe((data: any) => {
      this.teamHealth = data.team || [];
    });
  }

  loadCommitStats() {
    this.aiService.getCommitAnalysis(7).subscribe((data: any) => {
      this.commitStats = data.author_stats || {};
    });
  }

  // Find health data for a specific employee
  getHealthFor(name: string) {
    return this.teamHealth.find(t => t.name.toLowerCase() === name.toLowerCase());
  }

  // Find commit stats for a specific employee
  getCommitsFor(name: string) {
    // Basic matching, could be refined based on GitHub vs internal names
    const searchName = name.split(' ')[0].toLowerCase();
    for (const author in this.commitStats) {
      if (author.toLowerCase().includes(searchName)) {
        return this.commitStats[author];
      }
    }
    return null;
  }

  loadEmployees() {
    this.aiService.getEmployees().subscribe((data: any) => this.employees = data);
  }

  // 🚀 Open modal for a NEW member
  openAddModal() {
    this.isEditing = false;
    this.newEmp = { name: '', role: '', skills: '', email: '', rate: 50 };
    this.showModal = true;
  }

  // 🚀 Open modal to EDIT existing member
  editEmployee(emp: any) {
    this.isEditing = true;
    // Map array skills back to a comma-separated string for the input
    this.newEmp = { ...emp, skills: Array.isArray(emp.skills) ? emp.skills.join(', ') : emp.skills };
    this.showModal = true;
  }

  // 🚀 Delete member
  deleteEmployee(email: string) {
    if (confirm('Are you sure you want to remove this team member?')) {
      this.aiService.deleteEmployee(email).subscribe(() => {
        this.loadEmployees();
      });
    }
  }
  goBackToDashboard() {
    this.goBack.emit(); // 🚀 Send signal to parent
  }

  // 🚀 Unified Save logic
  saveEmployee() {
    if (!this.newEmp.name || !this.newEmp.email) return;
    
    const skillsArray = typeof this.newEmp.skills === 'string' 
      ? this.newEmp.skills.split(',').map(s => s.trim()) 
      : this.newEmp.skills;

    if (this.isEditing) {
      this.aiService.updateEmployee(this.newEmp.email, { ...this.newEmp, skills: skillsArray })
        .subscribe(() => {
          this.loadEmployees();
          this.showModal = false;
        });
    } else {
      this.aiService.addEmployee(this.newEmp.name, this.newEmp.role, skillsArray, this.newEmp.email, this.newEmp.rate)
        .subscribe(() => {
          this.loadEmployees();
          this.showModal = false;
        });
    }
  }
}