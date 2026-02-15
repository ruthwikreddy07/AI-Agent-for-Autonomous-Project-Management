import { CommonModule } from '@angular/common';
import { Chart, registerables, ChartConfiguration, ChartOptions } from 'chart.js';
import { Component, OnInit, Output, EventEmitter, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { AiService } from '../ai.service';


Chart.register(...registerables);

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.css']
})
export class DashboardComponent implements OnInit, AfterViewInit {
  @Output() navigate = new EventEmitter<string>();
  @ViewChild('lineCanvas', { static: false }) lineCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('donutCanvas', { static: false }) donutCanvas!: ElementRef<HTMLCanvasElement>;

  // Variables bound to your HTML {{ }}
stats = {
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
  user_display_name: 'Project Manager' // 👈 ADD THIS LINE
};
  financeData: any[] = [];
  
  private lineChart!: Chart;
  private donutChart!: Chart;
  trelloUrl: string = ''; // 🚀 Variable to store the link
  constructor(private aiService: AiService) {} // 👈 Added AiService injection

  ngOnInit(): void {
    // 👈 Added this function call to fetch real data on load
    this.loadRealData();
    this.loadTrelloLink();
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
        total_budget: data.total_budget,    // 👈 MAP THIS
  current_project: data.current_project, // 👈 MAP THIS
  recent_projects: data.recent_projects,
  user_display_name: data.user_display_name  // 👈 MAP THIS
      };

      this.financeData = data.finance_table;

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
        data: this.lineChartData, // Uses static data as fallback initially
        options: this.lineChartOptions
      });
    }

    if (this.donutCanvas) {
      this.donutChart = new Chart(this.donutCanvas.nativeElement, {
        type: 'doughnut',
        data: this.donutChartData, // Uses static data as fallback initially
        options: this.donutChartOptions
      });
    }
  }


  onNavClick(view: string) {
  this.navigate.emit(view);
}

// 🚀 Add these below:
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