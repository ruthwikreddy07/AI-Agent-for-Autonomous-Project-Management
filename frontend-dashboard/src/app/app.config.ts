import { ApplicationConfig } from '@angular/core';
import { provideHttpClient } from '@angular/common/http'; // <--- THIS IS MISSING

export const appConfig: ApplicationConfig = {
  providers: [
    provideHttpClient() // <--- Adds the ability to use API calls
  ]
};