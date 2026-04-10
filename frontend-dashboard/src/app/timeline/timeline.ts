import { Component, OnInit, Output, EventEmitter, ViewChild, ElementRef, AfterViewInit, Inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService } from '../ai.service';

interface GanttTask {
  id: string;
  name: string;
  start_date: string | null;
  end_date: string | null;
  owner: string;
  status: string;
  epic_name: string;
  epic_color: string;
  depends_on: string[];
  estimated_hours: number;
  is_critical_path: boolean;
  // Computed
  x?: number;
  y?: number;
  width?: number;
  barColor?: string;
}

@Component({
  selector: 'app-timeline',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './timeline.html',
  styleUrls: ['./timeline.css']
})
export class TimelineComponent implements OnInit, AfterViewInit {
  @Output() navigate = new EventEmitter<string>();
  @ViewChild('ganttCanvas', { static: false }) canvasRef!: ElementRef<HTMLCanvasElement>;

  tasks: GanttTask[] = [];
  totalTasks = 0;
  isLoading = true;
  isBrowser: boolean;
  zoomLevel = 1;  // 1 = day, 2 = half-day
  filterEpic = '';
  epics: string[] = [];
  hoveredTask: GanttTask | null = null;
  tooltipX = 0;
  tooltipY = 0;

  // Gantt config
  private ROW_HEIGHT = 44;
  private HEADER_HEIGHT = 60;
  private LEFT_PANEL_WIDTH = 280;
  private DAY_WIDTH = 50;
  private ctx!: CanvasRenderingContext2D;
  private canvas!: HTMLCanvasElement;
  private dateRange: Date[] = [];
  private minDate!: Date;
  private maxDate!: Date;
  private scrollX = 0;
  private scrollY = 0;
  private dpr = 1;

  constructor(private aiService: AiService, @Inject(PLATFORM_ID) platformId: Object) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  ngOnInit() { this.loadData(); }

  ngAfterViewInit() {
    if (this.isBrowser && this.canvasRef) {
      setTimeout(() => this.initCanvas(), 100);
    }
  }

  loadData() {
    this.isLoading = true;
    this.aiService.getGanttData().subscribe({
      next: (data: any) => {
        this.tasks = data.tasks || [];
        this.totalTasks = data.total || 0;
        this.epics = [...new Set(this.tasks.map(t => t.epic_name))];
        this.computeDateRange();
        this.isLoading = false;
        if (this.isBrowser) setTimeout(() => this.render(), 50);
      },
      error: () => { this.isLoading = false; }
    });
  }

  computeDateRange() {
    const now = new Date();
    let min = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 3);
    let max = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 21);

    for (const t of this.tasks) {
      if (t.start_date) {
        const s = new Date(t.start_date);
        if (s < min) min = s;
      }
      if (t.end_date) {
        const e = new Date(t.end_date);
        if (e > max) max = e;
      }
    }

    this.minDate = min;
    this.maxDate = new Date(max.getTime() + 3 * 86400000);
    this.dateRange = [];
    for (let d = new Date(min); d <= this.maxDate; d.setDate(d.getDate() + 1)) {
      this.dateRange.push(new Date(d));
    }
  }

  initCanvas() {
    if (!this.canvasRef) return;
    this.canvas = this.canvasRef.nativeElement;
    const parent = this.canvas.parentElement!;
    this.dpr = window.devicePixelRatio || 1;
    this.canvas.width = parent.offsetWidth * this.dpr;
    this.canvas.height = Math.max(parent.offsetHeight, (this.tasks.length + 2) * this.ROW_HEIGHT + this.HEADER_HEIGHT) * this.dpr;
    this.canvas.style.width = parent.offsetWidth + 'px';
    this.canvas.style.height = Math.max(parent.offsetHeight, (this.tasks.length + 2) * this.ROW_HEIGHT + this.HEADER_HEIGHT) + 'px';
    this.ctx = this.canvas.getContext('2d')!;
    this.ctx.scale(this.dpr, this.dpr);

    // Mouse events
    this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
    this.canvas.addEventListener('mouseleave', () => { this.hoveredTask = null; });

    this.render();
  }

  render() {
    if (!this.ctx) { this.initCanvas(); return; }

    const filteredTasks = this.filterEpic
      ? this.tasks.filter(t => t.epic_name === this.filterEpic)
      : this.tasks;

    const w = this.canvas.width / this.dpr;
    const h = this.canvas.height / this.dpr;
    this.ctx.clearRect(0, 0, w, h);

    this.drawHeader(w);
    this.drawGrid(w, filteredTasks.length);
    this.drawTodayLine(filteredTasks.length);
    this.drawTasks(filteredTasks);
    this.drawDependencyArrows(filteredTasks);
    this.drawLeftPanel(filteredTasks);
  }

  drawHeader(width: number) {
    const ctx = this.ctx;
    const dayW = this.DAY_WIDTH * this.zoomLevel;

    // Header background
    ctx.fillStyle = '#FAFAFF';
    ctx.fillRect(0, 0, width, this.HEADER_HEIGHT);
    ctx.strokeStyle = '#E8E8EE';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, this.HEADER_HEIGHT);
    ctx.lineTo(width, this.HEADER_HEIGHT);
    ctx.stroke();

    // Date labels
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    for (let i = 0; i < this.dateRange.length; i++) {
      const x = this.LEFT_PANEL_WIDTH + i * dayW - this.scrollX;
      if (x < this.LEFT_PANEL_WIDTH - dayW || x > width + dayW) continue;

      const d = this.dateRange[i];
      const isToday = d.toDateString() === today.toDateString();
      const isWeekend = d.getDay() === 0 || d.getDay() === 6;

      // Month label (on 1st day)
      if (d.getDate() === 1 || i === 0) {
        ctx.fillStyle = '#6C5DD3';
        ctx.font = 'bold 11px Inter, sans-serif';
        ctx.fillText(d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }), x + 4, 18);
      }

      // Day number
      ctx.fillStyle = isToday ? '#6C5DD3' : isWeekend ? '#C0C0CC' : '#808191';
      ctx.font = `${isToday ? 'bold' : 'normal'} 12px Inter, sans-serif`;
      ctx.fillText(d.getDate().toString(), x + dayW / 2 - 6, 38);

      // Day name
      ctx.font = '9px Inter, sans-serif';
      ctx.fillText(['S', 'M', 'T', 'W', 'T', 'F', 'S'][d.getDay()], x + dayW / 2 - 3, 52);
    }

    // Left panel header
    ctx.fillStyle = '#FAFAFF';
    ctx.fillRect(0, 0, this.LEFT_PANEL_WIDTH, this.HEADER_HEIGHT);
    ctx.fillStyle = '#808191';
    ctx.font = 'bold 11px Inter, sans-serif';
    ctx.fillText('TASK NAME', 16, 36);
  }

  drawGrid(width: number, taskCount: number) {
    const ctx = this.ctx;
    const dayW = this.DAY_WIDTH * this.zoomLevel;
    const totalH = this.HEADER_HEIGHT + taskCount * this.ROW_HEIGHT;

    for (let i = 0; i < this.dateRange.length; i++) {
      const x = this.LEFT_PANEL_WIDTH + i * dayW - this.scrollX;
      const d = this.dateRange[i];
      const isWeekend = d.getDay() === 0 || d.getDay() === 6;

      if (isWeekend) {
        ctx.fillStyle = '#F8F8FC';
        ctx.fillRect(x, this.HEADER_HEIGHT, dayW, totalH);
      }

      ctx.strokeStyle = '#F0F0F4';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(x, this.HEADER_HEIGHT);
      ctx.lineTo(x, totalH);
      ctx.stroke();
    }

    // Row lines
    for (let i = 0; i <= taskCount; i++) {
      const y = this.HEADER_HEIGHT + i * this.ROW_HEIGHT;
      ctx.strokeStyle = '#F0F0F4';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(this.LEFT_PANEL_WIDTH, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }

  drawTodayLine(taskCount: number) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const dayIndex = this.dateRange.findIndex(d => d.toDateString() === today.toDateString());
    if (dayIndex === -1) return;

    const dayW = this.DAY_WIDTH * this.zoomLevel;
    const x = this.LEFT_PANEL_WIDTH + dayIndex * dayW + dayW / 2 - this.scrollX;
    const totalH = this.HEADER_HEIGHT + taskCount * this.ROW_HEIGHT;

    this.ctx.strokeStyle = '#FF754C';
    this.ctx.lineWidth = 2;
    this.ctx.setLineDash([4, 3]);
    this.ctx.beginPath();
    this.ctx.moveTo(x, this.HEADER_HEIGHT);
    this.ctx.lineTo(x, totalH);
    this.ctx.stroke();
    this.ctx.setLineDash([]);

    // Today label
    this.ctx.fillStyle = '#FF754C';
    this.ctx.font = 'bold 9px Inter, sans-serif';
    this.ctx.fillText('TODAY', x - 16, this.HEADER_HEIGHT - 4);
  }

  drawTasks(tasks: GanttTask[]) {
    const ctx = this.ctx;
    const dayW = this.DAY_WIDTH * this.zoomLevel;
    const barH = 26;
    const barRadius = 8;

    for (let i = 0; i < tasks.length; i++) {
      const t = tasks[i];
      const y = this.HEADER_HEIGHT + i * this.ROW_HEIGHT + (this.ROW_HEIGHT - barH) / 2;

      if (!t.start_date || !t.end_date) {
        // Draw a placeholder dot
        const dotX = this.LEFT_PANEL_WIDTH + 40 - this.scrollX;
        ctx.fillStyle = '#C0C0CC';
        ctx.beginPath();
        ctx.arc(dotX, y + barH / 2, 4, 0, Math.PI * 2);
        ctx.fill();
        t.x = dotX; t.y = y; t.width = 0;
        continue;
      }

      const start = new Date(t.start_date);
      const end = new Date(t.end_date);
      const startDayIndex = Math.max(0, Math.round((start.getTime() - this.minDate.getTime()) / 86400000));
      const duration = Math.max(1, Math.round((end.getTime() - start.getTime()) / 86400000) + 1);

      const x = this.LEFT_PANEL_WIDTH + startDayIndex * dayW - this.scrollX;
      const barW = duration * dayW;

      // Store position for hover
      t.x = x; t.y = y; t.width = barW;

      // Bar color by status
      let fillColor = t.epic_color || '#6C5DD3';
      if (t.status === 'done') fillColor = '#34AA44';
      else if (t.status === 'in_progress') fillColor = '#3F8CFF';
      t.barColor = fillColor;

      // Critical path glow
      if (t.is_critical_path) {
        ctx.shadowColor = '#FF754C';
        ctx.shadowBlur = 8;
      }

      // Draw bar
      ctx.fillStyle = fillColor;
      ctx.beginPath();
      ctx.roundRect(x, y, barW, barH, barRadius);
      ctx.fill();

      // Reset shadow
      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;

      // Critical path border
      if (t.is_critical_path) {
        ctx.strokeStyle = '#FF754C';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.roundRect(x, y, barW, barH, barRadius);
        ctx.stroke();
      }

      // Progress fill for in_progress
      if (t.status === 'in_progress') {
        ctx.fillStyle = 'rgba(255,255,255,0.25)';
        ctx.beginPath();
        ctx.roundRect(x, y, barW * 0.5, barH, barRadius);
        ctx.fill();
      }

      // Task name on bar
      if (barW > 60) {
        ctx.fillStyle = 'white';
        ctx.font = '11px Inter, sans-serif';
        const maxTextW = barW - 16;
        let text = t.name;
        if (ctx.measureText(text).width > maxTextW) {
          while (text.length > 3 && ctx.measureText(text + '...').width > maxTextW) text = text.slice(0, -1);
          text += '...';
        }
        ctx.fillText(text, x + 8, y + barH / 2 + 4);
      }
    }
  }

  drawDependencyArrows(tasks: GanttTask[]) {
    const ctx = this.ctx;
    const barH = 26;

    for (const task of tasks) {
      if (!task.depends_on || task.depends_on.length === 0) continue;
      if (!task.x || !task.width) continue;

      for (const depName of task.depends_on) {
        const depTask = tasks.find(t => t.name.toLowerCase().includes(depName.toLowerCase()));
        if (!depTask || !depTask.x) continue;

        const fromX = (depTask.x || 0) + (depTask.width || 0);
        const fromY = (depTask.y || 0) + barH / 2;
        const toX = task.x;
        const toY = (task.y || 0) + barH / 2;

        ctx.strokeStyle = task.is_critical_path ? '#FF754C' : '#B0B0C0';
        ctx.lineWidth = task.is_critical_path ? 2 : 1.5;
        ctx.setLineDash(task.is_critical_path ? [] : [3, 2]);

        ctx.beginPath();
        const midX = fromX + (toX - fromX) * 0.5;
        ctx.moveTo(fromX, fromY);
        ctx.bezierCurveTo(midX, fromY, midX, toY, toX, toY);
        ctx.stroke();
        ctx.setLineDash([]);

        // Arrow head
        ctx.fillStyle = ctx.strokeStyle;
        ctx.beginPath();
        ctx.moveTo(toX, toY);
        ctx.lineTo(toX - 6, toY - 4);
        ctx.lineTo(toX - 6, toY + 4);
        ctx.closePath();
        ctx.fill();
      }
    }
  }

  drawLeftPanel(tasks: GanttTask[]) {
    const ctx = this.ctx;

    // Panel background
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, this.HEADER_HEIGHT, this.LEFT_PANEL_WIDTH, tasks.length * this.ROW_HEIGHT);

    // Panel border
    ctx.strokeStyle = '#E8E8EE';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(this.LEFT_PANEL_WIDTH, 0);
    ctx.lineTo(this.LEFT_PANEL_WIDTH, this.HEADER_HEIGHT + tasks.length * this.ROW_HEIGHT);
    ctx.stroke();

    for (let i = 0; i < tasks.length; i++) {
      const t = tasks[i];
      const y = this.HEADER_HEIGHT + i * this.ROW_HEIGHT;

      // Row hover highlight
      if (this.hoveredTask && this.hoveredTask.id === t.id) {
        ctx.fillStyle = '#F5F3FF';
        ctx.fillRect(0, y, this.LEFT_PANEL_WIDTH, this.ROW_HEIGHT);
      }

      // Status dot
      const dotColor = t.status === 'done' ? '#34AA44' : t.status === 'in_progress' ? '#3F8CFF' : '#FFCE73';
      ctx.fillStyle = dotColor;
      ctx.beginPath();
      ctx.arc(20, y + this.ROW_HEIGHT / 2, 4, 0, Math.PI * 2);
      ctx.fill();

      // Task name
      ctx.fillStyle = '#11142D';
      ctx.font = '12px Inter, sans-serif';
      let name = t.name;
      const maxW = this.LEFT_PANEL_WIDTH - 60;
      if (ctx.measureText(name).width > maxW) {
        while (name.length > 3 && ctx.measureText(name + '...').width > maxW) name = name.slice(0, -1);
        name += '...';
      }
      ctx.fillText(name, 34, y + this.ROW_HEIGHT / 2 + 4);

      // Row divider
      ctx.strokeStyle = '#F0F0F4';
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(0, y + this.ROW_HEIGHT);
      ctx.lineTo(this.LEFT_PANEL_WIDTH, y + this.ROW_HEIGHT);
      ctx.stroke();
    }
  }

  onMouseMove(e: MouseEvent) {
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const barH = 26;

    this.hoveredTask = null;
    for (const t of this.tasks) {
      if (t.x !== undefined && t.y !== undefined && t.width !== undefined) {
        if (mx >= t.x && mx <= t.x + t.width && my >= t.y && my <= t.y + barH) {
          this.hoveredTask = t;
          this.tooltipX = e.clientX + 12;
          this.tooltipY = e.clientY - 10;
          break;
        }
      }
    }
    // Also check left panel for hover highlighting
    this.render();
  }

  zoomIn() {
    this.zoomLevel = Math.min(3, this.zoomLevel + 0.5);
    this.render();
  }

  zoomOut() {
    this.zoomLevel = Math.max(0.5, this.zoomLevel - 0.5);
    this.render();
  }

  filterByEpic(epic: string) {
    this.filterEpic = this.filterEpic === epic ? '' : epic;
    this.render();
  }

  onNavClick(view: string) { this.navigate.emit(view); }
}
