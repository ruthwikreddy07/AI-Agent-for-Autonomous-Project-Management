import { ApplicationConfig } from '@angular/core';
import { provideHttpClient, withFetch } from '@angular/common/http'; // <--- Provides HTTP client (with fetch for SSR)

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient(withFetch()) // <--- Adds the ability to use API calls (and SSR-safe fetch)
  ]
};