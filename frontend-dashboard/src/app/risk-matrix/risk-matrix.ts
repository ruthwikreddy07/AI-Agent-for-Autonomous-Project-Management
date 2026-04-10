import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService } from '../ai.service';

@Component({
  selector: 'app-risk-matrix',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './risk-matrix.html',
  styleUrls: ['./risk-matrix.css']
})
export class RiskMatrixComponent implements OnInit {
  @Output() navigate = new EventEmitter<string>();

  risks: any[] = [];
  loading: boolean = true;
  matrix: any[][] = []; // 5x5 grid

  // 1 = Very Low, 2 = Low, 3 = Medium, 4 = High, 5 = Very High
  impactLabels = ['VL', 'L', 'M', 'H', 'VH'];
  probLabels = ['VH', 'H', 'M', 'L', 'VL']; // Top to bottom

  constructor(private aiService: AiService) {
    this.initMatrix();
  }

  ngOnInit() {
    this.loadRisks();
  }

  initMatrix() {
    this.matrix = Array(5).fill(null).map(() => Array(5).fill(null).map(() => []));
  }

  loadRisks() {
    this.loading = true;
    this.aiService.getRiskRegister().subscribe({
      next: (data) => {
        this.risks = data;
        this.populateMatrix();
        this.loading = false;
      },
      error: (e) => {
        console.error("Failed to load risks", e);
        this.loading = false;
      }
    });
  }

  populateMatrix() {
    this.initMatrix();
    this.risks.forEach(r => {
      // prob 1-5, impact 1-5
      // Matrix rows: 0 is prob 5, 4 is prob 1
      const row = 5 - Math.max(1, Math.min(5, r.probability));
      // Matrix cols: 0 is impact 1, 4 is impact 5
      const col = Math.max(1, Math.min(5, r.impact)) - 1;
      this.matrix[row][col].push(r);
    });
  }

  getRiskColor(prob: number, imp: number): string {
    const score = prob * imp;
    if (score >= 16) return 'risk-critical'; // Red
    if (score >= 10) return 'risk-high';     // Orange
    if (score >= 5) return 'risk-medium';    // Yellow
    return 'risk-low';                       // Green
  }

  getSeverityIcon(score: number): string {
    if (score >= 16) return '🔴';
    if (score >= 10) return '🟠';
    if (score >= 5) return '🟡';
    return '🟢';
  }

  triggerAIPredict() {
    this.loading = true;
    this.aiService.predictRisks().subscribe({
      next: (res) => {
        // AI tool populated Mongo, now reload
        this.loadRisks();
      },
      error: () => this.loading = false
    });
  }

  updateRiskStatus(risk: any, newStatus: string) {
    risk.status = newStatus;
    this.aiService.updateRisk(risk.id, { status: newStatus }).subscribe();
  }

  goBack() {
    this.navigate.emit('dashboard');
  }
}
