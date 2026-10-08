import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_CONFIG_PATH = path.join(__dirname, '..', 'fleet.config.json');

export function loadFleetConfig(configPath = process.env.FLEET_CONFIG || DEFAULT_CONFIG_PATH) {
  const raw = readFileSync(configPath, 'utf-8');
  const parsed = JSON.parse(raw);

  if (!Array.isArray(parsed.vehicles)) {
    throw new Error(`fleet config at ${configPath} must have a "vehicles" array`);
  }

  for (const v of parsed.vehicles) {
    if (!v.id || !v.wsUrl) {
      throw new Error(`each vehicle entry needs "id" and "wsUrl": ${JSON.stringify(v)}`);
    }
  }

  return parsed.vehicles;
}
