import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Chart, registerables, ChartConfiguration, ChartOptions } from 'chart.js';
import { Component, OnInit, Output, EventEmitter, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { AiService } from '../ai.service';
import { ChangeDetectorRef } from '@angular/core';


Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class DashboardComponent implements OnInit, AfterViewInit {
  @Output() navigate = new EventEmitter<string>();
  @ViewChild('lineCanvas', { static: false }) lineCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('donutCanvas', { static: false }) donutCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('burndownCanvas', { static: false }) burndownCanvas!: ElementRef<HTMLCanvasElement>;

  // Variables bound to your HTML {{ }}
stats: any = {
  tasks_due: 0,
  overdue: 0,
  active: 0,
  resolved_risks: 0,
  total_team: 0,
  in_progress: 0,
  not_started: 0,
  total_budget: '$0',
  current_project: '',
  recent_projects: [] as string[],
  user_display_name: 'Project Manager',
  team_workload: [],
  burn_percentage: 0,
  burndown_chart: null,
  user_role: 'developer'
};
  isPM = false;
  financeData: any[] = [];
  recentMeetings: any[] = [];
  scopeHealth: any = null;

  // --- Multi-Project ---
  projects: any[] = [];
  activeProjectName: string = '';
  showProjectModal = false;
  newProject = { name: '', trello_board_url: '', n8n_trello_webhook: '', n8n_get_cards_url: '' };
  
  private lineChart!: Chart;
  private donutChart!: Chart;
  private burndownChart!: Chart;
  trelloUrl: string = ''; // 🚀 Variable to store the link
  constructor(private cdr: ChangeDetectorRef,private aiService: AiService) {} // 👈 Added AiService injection

  ngOnInit(): void {
    this.loadRealData();
    this.loadTrelloLink();
    this.loadProjects();
    this.loadSprint3Data();
  }

  ngAfterViewInit(): void {
    // Initial render with placeholders (optional, loadRealData will overwrite these)
    this.initCharts();
  }

  // 🚀 NEW FUNCTION: Bridges Frontend to Backend
  loadRealData() {
  this.aiService.getDashboardData().subscribe({
    next: (data: any) => {
      console.log('✅ Dashboard Data Received:', data);

      // 1. Map all individual stats for HTML display
      this.stats = {
        tasks_due: data.tasks_due,
        overdue: data.overdue,
        active: data.active,
        resolved_risks: data.resolved_risks,
        total_team: data.total_team,
        in_progress: data.in_progress,
        not_started: data.not_started,
        total_budget: data.total_budget,
        current_project: data.current_project,
        recent_projects: data.recent_projects,
        user_display_name: data.user_display_name,
        team_workload: data.team_workload || [],
        burn_percentage: data.burn_percentage || 0,
        burndown_chart: data.burndown_chart || null,
        user_role: data.user_role || 'developer'
      };
      this.isPM = (data.user_role === 'pm' || data.user_role === 'admin');

      this.financeData = data.finance_table;

      // Update Burndown Chart
      if (data.burndown_chart && this.burndownChart) {
        this.burndownChart.data.labels = data.burndown_chart.labels;
        this.burndownChart.data.datasets[0].data = data.burndown_chart.planned;
        this.burndownChart.data.datasets[1].data = data.burndown_chart.actual;
        this.burndownChart.update();
      }

      // 2. Update Line Chart (Curved lines logic)
      if (this.lineChart && data.line_chart) {
        data.line_chart.datasets.forEach((dataset: any) => {
          dataset.tension = 0.4; // 🔥 Smooth curves
          dataset.borderWidth = 3;
          dataset.pointRadius = 4;
        });
        this.lineChart.data = data.line_chart;
        this.lineChart.update();
      }

      // 3. Update Donut Chart (Segments logic)
      if (this.donutChart) {
        this.donutChart.data.datasets[0].data = [
          data.resolved_risks, 
          data.in_progress, 
          data.not_started
        ];
        this.donutChart.update();
      }
      this.cdr.detectChanges();
    },
    error: (err: any) => console.error('❌ Failed to fetch backend data:', err)
  });
}


getPercentage(value: number | undefined): string {
    const safeVal = value || 0;
    const total = (this.stats.resolved_risks || 0) + 
                  (this.stats.in_progress || 0) + 
                  (this.stats.not_started || 0);

    if (total === 0) return '0%';
    return Math.round((safeVal / total) * 100) + '%';
  }

  initCharts() {
    if (this.lineCanvas) {
      this.lineChart = new Chart(this.lineCanvas.nativeElement, {
        type: 'line',
        data: this.lineChartData,
        options: this.lineChartOptions
      });
    }

    if (this.donutCanvas) {
      this.donutChart = new Chart(this.donutCanvas.nativeElement, {
        type: 'doughnut',
        data: this.donutChartData,
        options: this.donutChartOptions
      });
    }

    if (this.burndownCanvas) {
      this.burndownChart = new Chart(this.burndownCanvas.nativeElement, {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Planned',
              data: [],
              borderColor: '#6C5DD3',
              backgroundColor: 'rgba(108,93,211,0.08)',
              tension: 0.4,
              borderWidth: 2,
              pointRadius: 3,
              fill: true
            },
            {
              label: 'Actual',
              data: [],
              borderColor: '#FF754C',
              backgroundColor: 'rgba(255,117,76,0.08)',
              tension: 0.4,
              borderWidth: 2,
              pointRadius: 3,
              borderDash: [5, 3],
              fill: true
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: '#F3F4F6' }, border: { display: false }, ticks: { precision: 0 } },
            x: { grid: { display: false }, border: { display: false } }
          }
        }
      });
    }
  }


  onNavClick(view: string) {
  this.navigate.emit(view);
}

// 🚀 Add these below:
loadSprint3Data() {
  this.aiService.getMeetings().subscribe({
    next: (data: any[]) => this.recentMeetings = data.slice(0, 3)
  });
  
  // Try to load active sprint scope health
  this.aiService.getSprints().subscribe({
    next: (sprints: any[]) => {
      const active = sprints.find(s => s.status === 'active');
      if (active) {
        this.aiService.getSprintScopeHealth(active.id).subscribe({
          next: (data) => this.scopeHealth = data
        });
      }
    }
  });
}

loadTrelloLink() {
  const savedLinks = localStorage.getItem('nexus_links');
  if (savedLinks) {
    const parsed = JSON.parse(savedLinks);
    this.trelloUrl = parsed.trello || ''; 
  }
}

openTrello() {
  if (this.trelloUrl) {
    window.open(this.trelloUrl, '_blank');
  } else {
    alert('⚠️ Please set your Trello Board URL in Settings first!');
  }
}

  // --- PROJECT METHODS ---
  loadProjects() {
    this.aiService.getProjects().subscribe({
      next: (data: any[]) => {
        this.projects = data;
        if (data.length > 0 && !this.activeProjectName) {
          this.activeProjectName = data[0].name;
        }
      },
      error: (err: any) => console.error('Failed to load projects:', err)
    });
  }

  switchProject(project: any) {
    this.activeProjectName = project.name;
    this.loadRealData();
  }

  createProject() {
    if (!this.newProject.name) return;
    this.aiService.createProject(this.newProject).subscribe({
      next: () => {
        this.showProjectModal = false;
        this.newProject = { name: '', trello_board_url: '', n8n_trello_webhook: '', n8n_get_cards_url: '' };
        this.loadProjects();
      },
      error: (err: any) => console.error('Failed to create project:', err)
    });
  }

  // --- WORKLOAD HELPER ---
  getWorkloadColor(status: string): string {
    switch (status) {
      case 'overloaded': return '#FF754C';
      case 'busy': return '#FFCE73';
      case 'available': return '#34AA44';
      default: return '#808191';
    }
  }

  // --- STATICS (Used as fallbacks or structure templates) ---
  
  public lineChartData: ChartConfiguration<'line'>['data'] = {
    labels: ['01 Feb', '03 Feb', '05 Feb', '07 Feb', '09 Feb', '11 Feb'],
    datasets: [{
        data: [0, 0, 0, 0, 0, 0], // Initialized at 0
        label: 'Tasks',
        borderColor: '#6C5DD3',
        backgroundColor: 'transparent',
        tension: 0.4,
        borderWidth: 2
    }]
  };

  public lineChartOptions: ChartOptions<'line'> = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    y: { 
      beginAtZero: true,      // ✅ Fixes jumping base
      grid: { color: '#F3F4F6', drawTicks: false }, 
      border: { display: false },
      ticks: {
        stepSize: 1,          // 🔥 Forces whole numbers (1, 2, 3...)
        precision: 0          // 🔥 Removes decimals (1.5, 2.5)
      }
    },
    x: { grid: { display: false }, border: { display: false } }
  }
};

  public donutChartData: ChartConfiguration<'doughnut'>['data'] = {
  labels: ['Completed', 'In Progress', 'Not Started'],
  datasets: [{
    data: [0, 0, 0], // Placeholder, filled by loadRealData
    backgroundColor: [
      '#6C5DD3', // Vibrant Purple (Completed)
      '#3F8CFF', // Bright Blue (In Progress)
      '#FFCE73'  // Soft Gold (Not Started)
    ],
    borderWidth: 0,           // ❌ Removes the black border
    hoverOffset: 4,
    borderRadius: 8      // Makes segment ends slightly rounded for a modern look
  }]
};

public donutChartOptions: ChartOptions<'doughnut'> = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '78%',              // Makes the ring thinner and more elegant
  plugins: {
    legend: { display: false } // We use our custom HTML legend instead
  }
};
}