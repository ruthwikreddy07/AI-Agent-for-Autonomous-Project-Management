import { ApplicationConfig } from '@angular/core';
import { provideRouter } from '@angular/router'; // 🚀 Added
import { routes } from './app.routes';           // 🚀 Added
import { provideHttpClient, withFetch } from '@angular/common/http';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),           // 👈 Connects your routes
    provideHttpClient(withFetch()),  // 👈 Keeps your modern HTTP config
  ]
};