import express from 'express';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import { loadFleetConfig } from './config.js';
import { FleetStore } from './fleetStore.js';
import { connectFleet } from './avConnector.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 4000;

const vehicles = loadFleetConfig();
const store = new FleetStore(vehicles);
connectFleet(vehicles, store);

const app = express();
app.use(express.static(path.join(__dirname, '..', 'public')));

app.get('/api/fleet', (req, res) => {
  res.json(store.list());
});

app.get('/api/fleet/:id', (req, res) => {
  const vehicle = store.get(req.params.id);
  if (!vehicle) {
    res.status(404).json({ error: `unknown vehicle id: ${req.params.id}` });
    return;
  }
  res.json(vehicle);
});

app.listen(PORT, () => {
  console.log(`Fleet management service listening on http://localhost:${PORT}`);
});
