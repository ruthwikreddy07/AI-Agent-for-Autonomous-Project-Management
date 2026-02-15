import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

// This line starts your App component and explicitly passes the appConfig 
// (which contains your routing, HTTP, and Chart settings).
bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));