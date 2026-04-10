import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AiService } from '../ai.service';

@Component({
  selector: 'app-backlog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './backlog.html',
  styleUrls: ['./backlog.css']
})
export class BacklogComponent implements OnInit {
  @Output() navigate = new EventEmitter<string>();

  tree: any[] = [];
  expandedEpics: Set<string> = new Set();
  expandedStories: Set<string> = new Set();
  isLoading = true;
  isPM = false;

  // Modal state
  showModal = false;
  modalType: 'epic' | 'story' | 'task' = 'epic';
  modalParentId = '';
  modalEpicId = '';
  modalData = { name: '', description: '', story_points: 0, assigned_to: '', color: '#6C5DD3' };

  // Stats
  totalEpics = 0;
  totalStories = 0;
  totalTasks = 0;
  totalPoints = 0;

  constructor(private aiService: AiService) {}

  ngOnInit() {
    this.isPM = this.aiService.isPM();
    this.loadTree();
  }

  loadTree() {
    this.isLoading = true;
    this.aiService.getWorkBreakdown().subscribe({
      next: (data: any[]) => {
        this.tree = data;
        this.calculateStats();
        this.isLoading = false;
        // Auto-expand all epics if few
        if (data.length <= 5) {
          data.forEach(e => this.expandedEpics.add(e.id));
        }
      },
      error: () => { this.isLoading = false; }
    });
  }

  calculateStats() {
    this.totalEpics = this.tree.length;
    this.totalStories = 0;
    this.totalTasks = 0;
    this.totalPoints = 0;
    for (const epic of this.tree) {
      for (const story of epic.stories || []) {
        if (story.type === 'story') {
          this.totalStories++;
          this.totalPoints += story.story_points || 0;
          this.totalTasks += (story.tasks || []).length;
        } else {
          this.totalTasks++; // Direct tasks under epic
        }
      }
    }
  }

  toggleEpic(epicId: string) {
    if (this.expandedEpics.has(epicId)) {
      this.expandedEpics.delete(epicId);
    } else {
      this.expandedEpics.add(epicId);
    }
  }

  toggleStory(storyId: string) {
    if (this.expandedStories.has(storyId)) {
      this.expandedStories.delete(storyId);
    } else {
      this.expandedStories.add(storyId);
    }
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'done': return '#34AA44';
      case 'in_progress': return '#3F8CFF';
      case 'todo': return '#FFCE73';
      case 'active': return '#6C5DD3';
      default: return '#808191';
    }
  }

  getStatusLabel(status: string): string {
    switch (status) {
      case 'done': return 'Done';
      case 'in_progress': return 'In Progress';
      case 'todo': return 'To Do';
      case 'active': return 'Active';
      default: return status;
    }
  }

  // --- MODAL ACTIONS ---
  openAddEpic() {
    this.modalType = 'epic';
    this.modalParentId = '';
    this.modalEpicId = '';
    this.modalData = { name: '', description: '', story_points: 0, assigned_to: '', color: '#6C5DD3' };
    this.showModal = true;
  }

  openAddStory(epicId: string) {
    this.modalType = 'story';
    this.modalParentId = epicId;
    this.modalEpicId = epicId;
    this.modalData = { name: '', description: '', story_points: 0, assigned_to: '', color: '' };
    this.showModal = true;
  }

  openAddTask(storyId: string, epicId: string) {
    this.modalType = 'task';
    this.modalParentId = storyId;
    this.modalEpicId = epicId;
    this.modalData = { name: '', description: '', story_points: 0, assigned_to: '', color: '' };
    this.showModal = true;
  }

  saveItem() {
    if (!this.modalData.name.trim()) return;

    if (this.modalType === 'epic') {
      this.aiService.createEpic({
        name: this.modalData.name,
        description: this.modalData.description,
        color: this.modalData.color
      }).subscribe(() => { this.showModal = false; this.loadTree(); });

    } else if (this.modalType === 'story') {
      this.aiService.createStory({
        name: this.modalData.name,
        description: this.modalData.description,
        epic_id: this.modalParentId,
        story_points: this.modalData.story_points,
        assigned_to: this.modalData.assigned_to || 'Unassigned'
      }).subscribe(() => { this.showModal = false; this.loadTree(); });

    } else if (this.modalType === 'task') {
      this.aiService.createTask({
        name: this.modalData.name,
        description: this.modalData.description,
        story_id: this.modalParentId,
        epic_id: this.modalEpicId,
        assigned_to: this.modalData.assigned_to || 'Unassigned'
      }).subscribe(() => { this.showModal = false; this.loadTree(); });
    }
  }

  deleteEpic(epicId: string) {
    if (confirm('Delete this epic and ALL its stories/tasks?')) {
      this.aiService.deleteEpic(epicId).subscribe(() => this.loadTree());
    }
  }

  onNavClick(view: string) {
    this.navigate.emit(view);
  }
}
