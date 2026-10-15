/**
 * SWE-Agent Pro Full-Stack Server
 * Express backend providing agent execution, sandbox testing, benchmark evaluation,
 * human approval workflows, and mounting Vite middleware on port 3000.
 */

import express, { Request, Response } from 'express';
import { createServer as createViteServer } from 'vite';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json());

// In-memory run state & audit store
interface StoredRun {
  runId: string;
  state: any;
  approved?: boolean;
  approvalNotes?: string;
  approvedAt?: string;
  approvedBy?: string;
}

const runStore = new Map<string, StoredRun>();
const globalAuditTrail: any[] = [];

// Sample issues registry
const SAMPLE_ISSUES = [
  {
    key: 'paginator_offset',
    id: 'ISSUE-PRO-101',
    title: 'QuerySet.paginate 1-based offset calculation skips items',
    category: 'Off-by-one / Arithmetic',
    repoPath: path.resolve(process.cwd(), 'sample_repos/paginator_offset'),
    testCmd: 'python3 -m unittest test_paginator.py',
    description: `### Title: Pagination offset bug in QuerySet.paginate()

### Expected Behavior:
QuerySet.paginate(page=1, page_size=10) should return items 0 through 9. Page 2 should return items 10 through 19.

### Observed Behavior:
QuerySet.paginate(page=2, page_size=10) returns items 20 through 29 due to direct multiplication \`offset = page * page_size\`.

### Steps to Reproduce:
1. Initialize QuerySet with range(30)
2. Call qs.paginate(page=2, page_size=10)
3. Check first returned element ID (observed: 20, expected: 10)

### Constraints:
- Preserve existing public QuerySet API
- Must maintain backward compatibility for 1-based indexing contracts`,
  },
  {
    key: 'config_null_guard',
    id: 'ISSUE-PRO-102',
    title: 'TypeError: NoneType is not subscriptable in load_setting',
    category: 'Unhandled None / Crash',
    repoPath: path.resolve(process.cwd(), 'sample_repos/config_null_guard'),
    testCmd: 'python3 -m unittest test_config.py',
    description: `### Title: Unguarded subscript access crashes config loader

### Expected Behavior:
load_setting(config, "port", default=3000) should return 3000 when config is None.

### Observed Behavior:
Raises TypeError: 'NoneType' object is not subscriptable when callers pass uninitialized or None dictionary.

### Steps to Reproduce:
1. Call \`load_setting(None, "port", 3000)\`
2. Observer uncaught TypeError crash

### Constraints:
- Must safely return fallback default
- Must not mask genuine non-None dictionary lookups`,
  },
  {
    key: 'route_slash_normalizer',
    id: 'ISSUE-PRO-103',
    title: 'HTTP Router fails route matching when trailing slash is present',
    category: 'API Routing / Sanitization',
    repoPath: path.resolve(process.cwd(), 'sample_repos/route_slash_normalizer'),
    testCmd: 'python3 -m unittest test_router.py',
    description: `### Title: Router route equality mismatch on trailing slash

### Expected Behavior:
Request path \`/api/v1/users/\` should match registered route \`/api/v1/users\`.

### Observed Behavior:
Returns 404 Route Not Found because exact string comparison fails on trailing slashes.

### Steps to Reproduce:
1. Register endpoint \`/api/v1/users\`
2. Issue request for \`/api/v1/users/\`
3. Function \`match_endpoint\` returns False

### Constraints:
- RFC 3986 path normalization compliance
- Preserve base path extraction helper`,
  },
];

// Helper to run python CLI
function runPythonCommand(args: string[]): Promise<{ stdout: string; stderr: string; code: number }> {
  return new Promise((resolve) => {
    const pythonProc = spawn('python3', args, {
      cwd: process.cwd(),
      env: {
        ...process.env,
        PYTHONPATH: process.cwd(),
      },
    });

    let stdout = '';
    let stderr = '';

    pythonProc.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    pythonProc.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    pythonProc.on('close', (code) => {
      resolve({ stdout, stderr, code: code || 0 });
    });
  });
}

// REST Endpoints

// 1. Get sample issues
app.get('/api/sample-issues', (_req: Request, res: Response) => {
  res.json({
    success: true,
    issues: SAMPLE_ISSUES.map(({ key, id, title, category, testCmd, description }) => ({
      key,
      id,
      title,
      category,
      testCmd,
      description,
    })),
  });
});

// 2. Start bug hunt
app.post('/api/hunt', async (req: Request, res: Response) => {
  try {
    const { issue_text, repo_key, issue_id, test_cmd } = req.body;

    let targetRepoPath = '';
    let selectedTestCmd = test_cmd || '';

    if (repo_key) {
      const found = SAMPLE_ISSUES.find((s) => s.key === repo_key);
      if (found) {
        targetRepoPath = found.repoPath;
        if (!selectedTestCmd) selectedTestCmd = found.testCmd;
      }
    }

    if (!targetRepoPath) {
      targetRepoPath = path.resolve(process.cwd(), 'sample_repos/paginator_offset');
    }

    const args = [
      '-m',
      'sweagent_pro.cli',
      'hunt',
      '--repo',
      targetRepoPath,
      '--issue',
      issue_text || 'Fix offset issue',
      '--json',
    ];

    if (issue_id) {
      args.push('--issue-id', issue_id);
    }
    if (selectedTestCmd) {
      args.push('--test-cmd', selectedTestCmd);
    }

    const result = await runPythonCommand(args);

    let stateObj: any = null;
    try {
      stateObj = JSON.parse(result.stdout);
    } catch {
      return res.status(500).json({
        success: false,
        error: 'Failed to parse python agent output',
        rawOutput: result.stdout,
        rawError: result.stderr,
      });
    }

    // Save to run store
    runStore.set(stateObj.run_id, {
      runId: stateObj.run_id,
      state: stateObj,
    });

    if (stateObj.audit_trail) {
      globalAuditTrail.push(...stateObj.audit_trail);
    }

    res.json({
      success: true,
      data: stateObj,
    });
  } catch (err: any) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// 3. Human Approval Gate
app.post('/api/approve-patch', async (req: Request, res: Response) => {
  try {
    const { run_id, approved, notes, actor } = req.body;
    const stored = runStore.get(run_id);

    if (!stored) {
      return res.status(404).json({ success: false, error: 'Run not found' });
    }

    stored.approved = Boolean(approved);
    stored.approvalNotes = notes || '';
    stored.approvedAt = new Date().toISOString();
    stored.approvedBy = actor || 'Staff Lead Engineer';

    const auditEntry = {
      id: `AUD-APP-${Date.now().toString().slice(-4)}`,
      timestamp: Date.now() / 1000,
      actor: stored.approvedBy,
      action: approved ? 'HUMAN_APPROVED_PATCH' : 'HUMAN_REJECTED_PATCH',
      details: {
        run_id,
        notes: stored.approvalNotes,
        decision: approved ? 'APPROVED_FOR_RELEASE' : 'REJECTED_NEEDS_WORK',
      },
      approved: stored.approved,
      reviewer_notes: stored.approvalNotes,
    };

    stored.state.audit_trail.push(auditEntry);
    globalAuditTrail.push(auditEntry);

    res.json({
      success: true,
      message: approved ? 'Patch approved successfully and marked safe to merge' : 'Patch rejected with feedback notes',
      auditEntry,
    });
  } catch (err: any) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// 4. Run Benchmark
app.get('/api/benchmark', async (req: Request, res: Response) => {
  try {
    const maxIssues = req.query.max_issues ? parseInt(req.query.max_issues as string, 10) : 3;
    const args = ['-m', 'sweagent_pro.cli', 'eval', '--max-issues', String(maxIssues), '--json'];
    const result = await runPythonCommand(args);

    try {
      const benchObj = JSON.parse(result.stdout);
      res.json({ success: true, data: benchObj });
    } catch {
      res.status(500).json({
        success: false,
        error: 'Failed to parse benchmark JSON output',
        rawOutput: result.stdout,
        rawError: result.stderr,
      });
    }
  } catch (err: any) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// 5. Sandboxed execution on-demand
app.post('/api/sandbox-run', async (req: Request, res: Response) => {
  try {
    const { repo_key, test_cmd } = req.body;
    const found = SAMPLE_ISSUES.find((s) => s.key === repo_key);
    const repoPath = found ? found.repoPath : path.resolve(process.cwd(), 'sample_repos/paginator_offset');
    const cmd = test_cmd || 'python3 -m unittest test_paginator.py';

    const pythonCode = `
import json
from sweagent_pro.sandbox_tester import SandboxTester
tester = SandboxTester()
res = tester.run_sandboxed('${repoPath.replace(/'/g, "\\'")}', '${cmd.replace(/'/g, "\\'")}')
print(json.dumps(res.to_dict()))
`;
    const result = await runPythonCommand(['-c', pythonCode]);
    try {
      const parsed = JSON.parse(result.stdout);
      res.json({ success: true, result: parsed });
    } catch {
      res.status(500).json({ success: false, raw: result.stdout, error: result.stderr });
    }
  } catch (err: any) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// 6. Get Audit Trail
app.get('/api/audit-trail', (_req: Request, res: Response) => {
  res.json({
    success: true,
    totalEntries: globalAuditTrail.length,
    trail: globalAuditTrail.slice(-50).reverse(),
  });
});

// Mount Vite or serve static dist
async function startServer() {
  if (process.env.NODE_ENV === 'production' && fs.existsSync(path.resolve(process.cwd(), 'dist'))) {
    app.use(express.static(path.resolve(process.cwd(), 'dist')));
    app.get('*', (_req, res) => {
      res.sendFile(path.resolve(process.cwd(), 'dist', 'index.html'));
    });
  } else {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`SWE-Agent Pro server is running on http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
