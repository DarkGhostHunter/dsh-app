import { check } from '@tauri-apps/api/updater';

export async function checkForUpdates() {
  try {
    const res = await check();
    // res contains update info; show UI or call install
    console.log('Updater check result:', res);
  } catch (e) {
    console.error('Updater check failed', e);
  }
}