import { Component, OnInit, AfterViewInit, OnDestroy, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
// @ts-ignore
import { initLandingPage } from '../../assets/landing-animations.js';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './landing.html',
  styleUrls: ['./landing.css']
})
export class LandingComponent implements OnInit, AfterViewInit, OnDestroy {
  @Output() navigate = new EventEmitter<string>();
  
  constructor() {}

  ngOnInit(): void {
    // Basic init if needed
  }

  ngAfterViewInit(): void {
    // Check if we are in the browser
    if (typeof window !== 'undefined') {
      setTimeout(() => {
        try {
          initLandingPage();
        } catch(e) {
          console.error("Animation Init Error:", e);
        }
      }, 100);
    }
  }

  ngOnDestroy(): void {
    // Clean up observers if they exist on the window
    if (typeof window !== 'undefined') {
      if ((window as any)._terminalObserver) (window as any)._terminalObserver.disconnect();
      if ((window as any)._revealObserver) (window as any)._revealObserver.disconnect();
      if ((window as any)._statsObserver) (window as any)._statsObserver.disconnect();
      if ((window as any)._particleInterval) clearInterval((window as any)._particleInterval);
      if ((window as any)._canvasAnimFrame) cancelAnimationFrame((window as any)._canvasAnimFrame);
      if ((window as any)._cursorAnimFrame) cancelAnimationFrame((window as any)._cursorAnimFrame);
    }
  }

  navigateToDashboard() {
    this.navigate.emit('dashboard');
  }
}
