#!/usr/bin/env node
/**
 * Self-contained setup check for the HPC Agent runner.
 *
 * The runner, monitor, provider adapters, agent prompts, and HPC integration
 * files are vendored in this repository. No external upstream checkout is
 * required for normal setup.
 */
import { copyFileSync, existsSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const runnerDir = path.resolve(__dirname, '..');

const requiredFiles = [
  'src/server.js',
  'src/agent-runner.js',
  'src/chat.js',
  'src/key-pool.js',
  'src/oauth.js',
  'src/hpc-proxy.js',
  'src/hpc-tool.js',
  'src/providers/index.js',
  'monitor/package.json',
  'monitor/src/App.jsx',
  'monitor/src/components/layout/EndpointsPage.jsx',
  'monitor/src/components/layout/BudgetPage.jsx',
  'agent/worker.md',
  'bin/tbc-db.js',
];

console.log('Preparing HPC Agent runner...\n');
console.log('No external upstream checkout is required.');

const missing = requiredFiles.filter((file) => !existsSync(path.join(runnerDir, file)));
if (missing.length > 0) {
  console.error('\nMissing required runner files:');
  for (const file of missing) console.error(`  - ${file}`);
  console.error('\nThis checkout is incomplete. Restore the missing files, then rerun setup.');
  process.exit(1);
}

const envPath = path.join(runnerDir, '.env');
const envExamplePath = path.join(runnerDir, '.env.example');
if (!existsSync(envPath) && existsSync(envExamplePath)) {
  copyFileSync(envExamplePath, envPath);
  console.log('Created runner/.env from runner/.env.example');
}

console.log('\nRunner setup check passed.');
