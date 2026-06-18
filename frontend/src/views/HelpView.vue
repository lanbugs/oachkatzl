<script setup lang="ts">
import { ref } from 'vue'

const sections = [
  { id: 'overview',       label: 'Overview' },
  { id: 'dashboard',      label: 'Dashboard' },
  { id: 'projects',       label: 'Projects & Roles' },
  { id: 'members',        label: 'Project Members' },
  { id: 'keys',           label: 'Access Keys' },
  { id: 'custom-creds',   label: 'Custom Credentials' },
  { id: 'repositories',   label: 'Repositories' },
  { id: 'inventories',    label: 'Inventories' },
  { id: 'environments',   label: 'Environments & Variables' },
  { id: 'templates',      label: 'Templates' },
  { id: 'build-deploy',   label: 'Build & Deploy' },
  { id: 'survey',         label: 'Survey Variables' },
  { id: 'tasks',          label: 'Running Tasks' },
  { id: 'workflows',      label: 'Workflows' },
  { id: 'approval-gate',        label: 'Approval Gates' },
  { id: 'remote-approval-gate', label: 'Remote Approval' },
  { id: 'action-nodes',         label: 'Action Nodes' },
  { id: 'artifacts',      label: 'Artifact Cache' },
  { id: 'pip-proxy',      label: 'pip Package Proxy' },
  { id: 'scaling',        label: 'Scaling Workers' },
  { id: 'custom-workers', label: 'Custom Workers' },
  { id: 'custom-apps',   label: 'Custom Apps' },
  { id: 'schedules',      label: 'Schedules' },
  { id: 'tokens',         label: 'Execute Tokens' },
  { id: 'notifications',  label: 'Notifications' },
  { id: '2fa',            label: '2FA & Security' },
  { id: 'profile',        label: 'Profile' },
  { id: 'admin-users',    label: 'Admin: Users' },
  { id: 'admin-settings', label: 'Admin: Settings' },
  { id: 'about',          label: 'About' },
]

const activeSection = ref('overview')

function scrollTo(id: string) {
  activeSection.value = id
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <div class="flex gap-8 max-w-6xl mx-auto">

    <!-- Sticky sidebar nav -->
    <aside class="w-52 shrink-0">
      <div class="sticky top-4 bg-white border border-gray-200 rounded-xl overflow-hidden max-h-[calc(100vh-2rem)] flex flex-col">
        <div class="px-4 py-3 border-b border-gray-100 bg-gray-50">
          <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Documentation</p>
        </div>
        <nav class="p-2 space-y-0.5 overflow-y-auto flex-1">
          <button
            v-for="s in sections" :key="s.id"
            @click="scrollTo(s.id)"
            class="w-full text-left px-3 py-1.5 text-sm rounded-lg transition-colors"
            :class="activeSection === s.id
              ? 'bg-brand-50 text-brand-700 font-medium'
              : 'text-gray-600 hover:bg-gray-50'"
          >
            {{ s.label }}
          </button>
        </nav>
      </div>
    </aside>

    <!-- Content -->
    <div class="flex-1 min-w-0 space-y-12 pb-20">

      <!-- ── Overview ── -->
      <section id="overview">
        <h1 class="text-3xl font-bold text-gray-900 mb-2">Oachkatzl Documentation</h1>
        <p class="text-gray-500 text-sm mb-6">A self-hosted automation platform for running Ansible playbooks, shell scripts, and Python scripts.</p>

        <div class="prose-box">
          <p>Oachkatzl lets you define <strong>templates</strong> (what to run), attach resources (repositories, inventories, credentials), and execute them as <strong>tasks</strong> — manually, on a schedule, or via an API token. All output is streamed and archived.</p>

          <h3>Core concepts</h3>
          <table class="help-table">
            <tr><th>Concept</th><th>What it is</th></tr>
            <tr><td><strong>Project</strong></td><td>Top-level isolation boundary. Everything belongs to a project.</td></tr>
            <tr><td><strong>Template</strong></td><td>Reusable definition of what to execute and how.</td></tr>
            <tr><td><strong>Task</strong></td><td>A single execution of a template. Has status, log output, commit hash.</td></tr>
            <tr><td><strong>Access Key</strong></td><td>Encrypted credential (SSH key, password, Vault passphrase).</td></tr>
            <tr><td><strong>Repository</strong></td><td>Git repository cloned before each task run.</td></tr>
            <tr><td><strong>Inventory</strong></td><td>Ansible host list (static INI/YAML or a file in the repository).</td></tr>
            <tr><td><strong>Environment</strong></td><td>Extra variables and environment variables injected at run time.</td></tr>
          </table>
        </div>
      </section>

      <!-- ── Dashboard ── -->
      <section id="dashboard">
        <h2 class="help-h2">Dashboard</h2>
        <div class="prose-box">
          <p>The dashboard is the first screen after login. It gives a live overview of task activity and worker health across all your projects.</p>

          <h3>Task chart — last 7 days</h3>
          <p>A line chart shows the number of <strong>successful</strong> (green) and <strong>failed</strong> (red) tasks per day for the past seven days. Hover over a data point to see the exact counts. The totals for the period are shown below the chart.</p>

          <h3>Worker status</h3>
          <p>Each active <a @click.prevent="scrollTo('custom-workers')" href="#" class="text-brand-600 hover:underline">Worker Pool</a> is shown as a card with:</p>
          <table class="help-table">
            <thead><tr><th>Value</th><th>Meaning</th></tr></thead>
            <tbody>
              <tr><td>Workers online</td><td>Number of Celery worker processes currently connected to the broker.</td></tr>
              <tr><td>Workers busy</td><td>Workers currently executing at least one task.</td></tr>
              <tr><td>Active tasks</td><td>Total number of tasks running right now across all workers in this pool.</td></tr>
              <tr><td>Capacity</td><td>Total available task slots (sum of each worker's concurrency setting).</td></tr>
            </tbody>
          </table>
          <p>The worker status refreshes automatically every 15 seconds. A pool card turns amber when all capacity is used.</p>

          <div class="callout info">
            The default worker pool (<em>celery</em>) is always shown. Custom pools appear only when at least one worker for that pool is online.
          </div>
        </div>
      </section>

      <!-- ── Projects & Roles ── -->
      <section id="projects">
        <h2 class="help-h2">Projects &amp; Roles</h2>
        <div class="prose-box">
          <p>Every resource (templates, keys, repositories, …) belongs to exactly one project. Users are added to projects with a <strong>role</strong> that controls what they can do.</p>

          <table class="help-table">
            <tr><th>Role</th><th>Permissions</th></tr>
            <tr><td><span class="badge purple">owner</span></td><td>Full access including project deletion and member management.</td></tr>
            <tr><td><span class="badge blue">manager</span></td><td>Create/edit/delete all resources and run tasks. Cannot delete the project.</td></tr>
            <tr><td><span class="badge green">task_runner</span></td><td>Run tasks and view output. Cannot modify resources.</td></tr>
            <tr><td><span class="badge gray">guest</span></td><td>Read-only access. Cannot run tasks or edit anything.</td></tr>
          </table>

          <p>Global <strong>admins</strong> have owner-level access to every project regardless of membership.</p>
        </div>
      </section>

      <!-- ── Project Members ── -->
      <section id="members">
        <h2 class="help-h2">Project Members</h2>
        <div class="prose-box">
          <p>Members are managed under <strong>Project → Members</strong> in the sidebar. Only users with the <code>owner</code> or <code>manager</code> role (or a global admin) can add or remove members.</p>

          <h3>Adding a member</h3>
          <ol>
            <li>Click <strong>Add member</strong> in the top-right corner.</li>
            <li>Select a user from the dropdown — only users who are not already members are shown.</li>
            <li>Select a role (see <a @click.prevent="scrollTo('projects')" href="#" class="text-brand-600 hover:underline">Projects &amp; Roles</a> for role descriptions).</li>
            <li>Click <strong>Add member</strong>.</li>
          </ol>

          <h3>Changing a member's role</h3>
          <p>Use the role dropdown next to the member's name. The change takes effect immediately. An owner cannot demote themselves — another owner must do it.</p>

          <h3>Removing a member</h3>
          <p>Click the trash icon on the member row. The user immediately loses access to the project and all its resources.</p>

          <h3>LDAP-managed members</h3>
          <p>
            When <a @click.prevent="scrollTo('admin-settings')" href="#" class="text-brand-600 hover:underline">LDAP/AD</a> is enabled and group-to-project mappings are configured, users whose role comes from an LDAP group are marked with a purple <span class="badge blue" style="font-size:10px">LDAP</span> badge.
            Their role is determined by the LDAP group mapping and is re-synced on every login. Manual role changes for LDAP-managed members are overwritten on the user's next login.
          </p>
        </div>
      </section>

      <!-- ── Access Keys ── -->
      <section id="keys">
        <h2 class="help-h2">Access Keys</h2>
        <div class="prose-box">
          <p>Credentials stored encrypted in the database (Fernet/AES-256). The raw secret is <em>never</em> returned by the API — only a <code>has_secret</code> flag.</p>

          <table class="help-table">
            <tr><th>Type</th><th>Stored fields</th><th>Used for</th></tr>
            <tr><td><strong>SSH</strong></td><td>Private key + optional passphrase</td><td>Git clone over SSH, Ansible SSH connections</td></tr>
            <tr><td><strong>Login / Password</strong></td><td>Username + password</td><td>Ansible become, WinRM, custom scripts</td></tr>
            <tr><td><strong>Vault</strong></td><td>Ansible Vault password</td><td>Decrypting <code>ansible-vault</code> encrypted files</td></tr>
            <tr><td><strong>None</strong></td><td>—</td><td>Named placeholder (public repos, no auth needed)</td></tr>
          </table>

          <div class="callout info">
            <strong>Editing secrets:</strong> When editing a key, leave the secret fields blank to keep the existing credential. Fill them to replace it.
          </div>
        </div>
      </section>

      <!-- ── Custom Credentials ── -->
      <section id="custom-creds">
        <h2 class="help-h2">Custom Credentials</h2>
        <div class="prose-box">
          <p>
            Custom Credentials let you define your own credential schemas — input fields, labels, and
            exactly <em>how</em> those values are injected into tasks (as environment variables,
            Ansible extra vars, or temp files). Multiple credentials can be attached to a single template.
          </p>

          <div class="callout info">
            <strong>Two-level concept:</strong>
            An admin creates a <strong>Credential Type</strong> (the schema — what fields exist and how they are injected).
            Project members then create <strong>Credentials</strong> based on that type (the actual values, encrypted).
            Templates reference one or more Credentials.
          </div>

          <h3>Step 1 — Define a Credential Type (Admin)</h3>
          <p>Open <strong>Settings → Credential Types</strong> in the sidebar (visible to admins only) and click <em>New type</em>. Each type has two JSON fields:</p>

          <h3>Inputs schema</h3>
          <p>A JSON array describing the input fields users must fill in when creating a Credential of this type.</p>
          <pre v-pre class="code-block">[
  { "id": "username",    "label": "Username",    "type": "string",  "required": true  },
  { "id": "password",    "label": "Password",    "type": "secret",  "required": true  },
  { "id": "api_token",   "label": "API Token",   "type": "secret",  "required": false,
    "help_text": "Leave blank to use username/password instead" },
  { "id": "verify_ssl",  "label": "Verify SSL",  "type": "boolean", "required": false,
    "default": true }
]</pre>

          <table class="help-table mt-2">
            <tr><th>Field</th><th>Required</th><th>Description</th></tr>
            <tr><td><code>id</code></td><td>yes</td><td>Internal identifier — used in injector templates as <code v-pre>{{ id }}</code>.</td></tr>
            <tr><td><code>label</code></td><td>yes</td><td>Display name shown to users in the credential form.</td></tr>
            <tr><td><code>type</code></td><td>yes</td><td><code>string</code>, <code>secret</code> (masked), <code>boolean</code></td></tr>
            <tr><td><code>required</code></td><td>no</td><td>Whether the field must be filled. Default: <code>false</code>.</td></tr>
            <tr><td><code>default</code></td><td>no</td><td>Pre-filled value in the form.</td></tr>
            <tr><td><code>help_text</code></td><td>no</td><td>Short hint shown below the field.</td></tr>
          </table>

          <h3>Injectors schema</h3>
          <p>
            A JSON object with up to three sections — <code>env</code>, <code>extra_vars</code>, and <code>file</code> —
            describing how the credential fields are passed to the process.
            Use <code v-pre>{{ field_id }}</code> to reference a field value.
          </p>
          <pre v-pre class="code-block">{
  "env": {
    "MY_USERNAME":  "{{ username }}",
    "MY_TOKEN":     "{{ api_token }}"
  },
  "extra_vars": {
    "vault_user":   "{{ username }}",
    "verify_ssl":   "{{ verify_ssl }}"
  },
  "file": {
    "content": "{{ private_key }}",
    "var":     "KEY_FILE_PATH"
  }
}</pre>

          <table class="help-table mt-2">
            <tr><th>Section</th><th>Effect</th></tr>
            <tr>
              <td><code>env</code></td>
              <td>
                Key/value pairs added to the process environment before execution.
                Available in Bash as <code>$MY_USERNAME</code>, in Python as <code>os.environ["MY_USERNAME"]</code>.
              </td>
            </tr>
            <tr>
              <td><code>extra_vars</code></td>
              <td>
                Merged into <code>--extra-vars</code> for Ansible playbooks.
                Access as <code v-pre>{{ vault_user }}</code> in tasks and templates.
                Also exported as env vars for Bash/Python.
              </td>
            </tr>
            <tr>
              <td><code>file</code></td>
              <td>
                Writes <code>content</code> to a temporary file (mode 0600) and injects its path
                into the process environment under the name given by <code>var</code>.
                The file is securely deleted after the task finishes.
                Useful for private keys, certificates, kubeconfig files, etc.
              </td>
            </tr>
          </table>

          <h3>Step 2 — Create a Credential (Project)</h3>
          <p>
            Open the <strong>Keys &amp; Credentials</strong> tab inside your project and scroll down to the
            <em>Credentials</em> section. Click <em>New credential</em> and select the credential type —
            the form dynamically renders the input fields defined in that type's inputs schema.
            Secret fields are masked and stored encrypted.
          </p>
          <p>Multiple credentials of the same type can exist in a project (e.g. "Prod API key" and "Staging API key").</p>

          <h3>Step 3 — Attach credentials to a template</h3>
          <p>
            In the template editor, scroll to the <strong>Credentials</strong> section and check one or more
            credentials from the project. At task run time, all attached credentials are resolved
            and their injectors applied in order — env vars, extra vars, and file paths are all
            available to the playbook or script.
          </p>

          <div class="callout info">
            If two credentials inject the same environment variable or extra var, the one listed
            <em>last</em> on the template wins.
          </div>

          <h3>Practical example — HashiCorp Vault token</h3>
          <p><strong>Inputs schema:</strong></p>
          <pre v-pre class="code-block">[
  { "id": "vault_addr",  "label": "Vault Address", "type": "string", "required": true,
    "default": "https://vault.example.com" },
  { "id": "vault_token", "label": "Token",          "type": "secret", "required": true }
]</pre>
          <p><strong>Injectors schema:</strong></p>
          <pre v-pre class="code-block">{
  "env": {
    "VAULT_ADDR":  "{{ vault_addr }}",
    "VAULT_TOKEN": "{{ vault_token }}"
  }
}</pre>
          <p>Any script or playbook attached to a template using this credential can now call the Vault CLI or SDK directly — the environment variables are already set.</p>

          <h3>Practical example — kubeconfig file</h3>
          <p><strong>Inputs schema:</strong></p>
          <pre v-pre class="code-block">[
  { "id": "kubeconfig", "label": "kubeconfig (YAML)", "type": "secret", "required": true,
    "help_text": "Paste the full kubeconfig file content" }
]</pre>
          <p><strong>Injectors schema:</strong></p>
          <pre v-pre class="code-block">{
  "file": {
    "content": "{{ kubeconfig }}",
    "var":     "KUBECONFIG"
  }
}</pre>
          <p>
            Oachkatzl writes the kubeconfig content to a temp file, exports its path as
            <code>$KUBECONFIG</code>, and deletes the file after the task finishes.
            <code>kubectl</code> picks up the env var automatically.
          </p>

          <div class="callout warning">
            <strong>Security:</strong> Field values whose <code>type</code> is <code>secret</code>
            are stored encrypted in the database and never returned by the API.
            They are only decrypted inside the worker process immediately before task execution.
            Values containing <em>password</em>, <em>secret</em>, <em>token</em>, or <em>pass</em>
            in the field ID are automatically masked in the task run-parameter display.
          </div>
        </div>
      </section>

      <!-- ── Repositories ── -->
      <section id="repositories">
        <h2 class="help-h2">Repositories</h2>
        <div class="prose-box">
          <p>A Git repository that is cloned (or updated) into a temporary working directory before each task run. The HEAD commit hash is recorded on the task for traceability.</p>

          <h3>Fields</h3>
          <ul>
            <li><strong>Git URL</strong> — HTTPS or SSH URL. Example: <code>git@github.com:org/repo.git</code></li>
            <li><strong>Branch</strong> — Branch to check out. Default: <code>main</code></li>
            <li><strong>SSH Key</strong> — An <em>SSH</em>-type Access Key for private repositories.</li>
          </ul>

          <h3>SSH keys with passphrases</h3>
          <p>Oachkatzl automatically strips the passphrase from the key using <code>ssh-keygen</code> before passing it to git, so <code>BatchMode=yes</code> works correctly.</p>
        </div>
      </section>

      <!-- ── Inventories ── -->
      <section id="inventories">
        <h2 class="help-h2">Inventories</h2>
        <div class="prose-box">
          <p>Ansible host definitions. Not used for Bash or Python templates.</p>

          <table class="help-table">
            <tr><th>Type</th><th>Description</th></tr>
            <tr><td><strong>Static (INI)</strong></td><td>Paste the inventory content directly (classic <code>[group] host</code> format).</td></tr>
            <tr><td><strong>Static (YAML)</strong></td><td>Paste YAML inventory content directly.</td></tr>
            <tr><td><strong>File</strong></td><td>Path to an inventory file relative to the repository root. Cloned with the repo.</td></tr>
            <tr><td><strong>None</strong></td><td>No inventory. Useful when the playbook manages its own connection (e.g., <code>localhost</code>).</td></tr>
          </table>

          <h3>Keys on inventories</h3>
          <ul>
            <li><strong>SSH Key</strong> — passed to <code>ansible-playbook --private-key</code> for host login.</li>
            <li><strong>Become Key</strong> — used for privilege escalation (<code>sudo</code>). Can be SSH or Login/Password type.</li>
          </ul>
        </div>
      </section>

      <!-- ── Environments ── -->
      <section id="environments">
        <h2 class="help-h2">Environments &amp; Variables</h2>
        <div class="prose-box">
          <p>Reusable variable groups attached to templates. Two JSON objects are stored separately:</p>

          <table class="help-table">
            <tr><th>Field</th><th>How it's used</th></tr>
            <tr>
              <td><strong>Extra Variables</strong></td>
              <td>Ansible: passed as <code>--extra-vars @file</code>. Bash/Python: exported as environment variables.</td>
            </tr>
            <tr>
              <td><strong>Environment Variables</strong></td>
              <td>Set directly in the process environment before execution (all app types). Example: <code>AWS_REGION</code>, <code>KUBECONFIG</code>.</td>
            </tr>
          </table>

          <h3>Variable precedence (highest wins)</h3>
          <ol>
            <li>Survey answers provided at run time</li>
            <li>Per-run environment override (in the run dialog)</li>
            <li>Environment extra variables</li>
            <li>Environment env vars</li>
          </ol>

          <div class="callout warning">
            <strong>Security:</strong> Oachkatzl never passes its own internal variables (<code>OACHKATZL_JWT_SECRET</code>, <code>OACHKATZL_ENCRYPTION_KEY</code>, etc.) to subprocesses. Only what you explicitly configure is visible to scripts.
          </div>
        </div>
      </section>

      <!-- ── Templates ── -->
      <section id="templates">
        <h2 class="help-h2">Templates</h2>
        <div class="prose-box">
          <p>A template defines <em>what</em> gets executed, <em>how</em>, and with <em>which</em> resources.</p>

          <h3>App types</h3>
          <table class="help-table">
            <tr><th>Type</th><th>What runs</th><th>Extras</th></tr>
            <tr>
              <td><strong>Ansible</strong></td>
              <td><code>ansible-playbook &lt;playbook&gt;</code></td>
              <td>Inventory, Vault passwords, Galaxy auto-install</td>
            </tr>
            <tr>
              <td><strong>Bash / Shell</strong></td>
              <td><code>/bin/bash &lt;script&gt;</code></td>
              <td>—</td>
            </tr>
            <tr>
              <td><strong>Python</strong></td>
              <td>Python interpreter + script</td>
              <td>Auto <code>.venv</code> from <code>requirements.txt</code></td>
            </tr>
            <tr>
              <td><strong>Custom App</strong></td>
              <td>Admin-registered executable</td>
              <td>Any binary available in the worker image</td>
            </tr>
          </table>

          <h3>Ansible: automatic Galaxy install</h3>
          <p>Before running the playbook, Oachkatzl checks for requirements files and installs them into an isolated path:</p>
          <ul>
            <li><code>requirements.yml</code> → <code>ansible-galaxy role install</code> + <code>ansible-galaxy collection install</code></li>
            <li><code>roles/requirements.yml</code> → roles only</li>
            <li><code>collections/requirements.yml</code> → collections only</li>
          </ul>

          <h3>Python: automatic virtualenv</h3>
          <p>If a <code>requirements.txt</code> exists at the repository root, Oachkatzl automatically:</p>
          <ol>
            <li>Creates <code>.venv</code> in the working directory</li>
            <li>Runs <code>pip install -r requirements.txt</code> — via proxy if <code>OACHKATZL_PIP_INDEX_URL</code> is set (see <a @click.prevent="scrollTo('pip-proxy')" href="#" class="text-brand-600 hover:underline">pip Package Proxy</a>)</li>
            <li>Executes the script with the venv Python</li>
          </ol>

          <h3>Template options</h3>
          <table class="help-table">
            <tr><th>Option</th><th>Effect</th></tr>
            <tr><td>Allow override args</td><td>Operators can pass extra CLI arguments when starting a run.</td></tr>
            <tr><td>Allow parallel tasks</td><td>By default tasks from the same template queue sequentially. Enable this to allow concurrent runs.</td></tr>
            <tr><td>Suppress success alerts</td><td>Notifications are sent on failure but not on success for this template.</td></tr>
            <tr><td>Debug mode</td><td>Ansible: adds <code>-vvvv</code>. All types: extra logging from Oachkatzl itself (git steps, venv creation, galaxy install).</td></tr>
          </table>
        </div>
      </section>

      <!-- ── Build & Deploy ── -->
      <section id="build-deploy">
        <h2 class="help-h2">Build &amp; Deploy</h2>
        <div class="prose-box">
          <div class="callout info">
            Build and Deploy are <strong>template types</strong> (not app types). The underlying execution is the same — what changes is the metadata tracking and the deploy→build relationship.
          </div>

          <h3>Template type: Task (default)</h3>
          <p>A standard run. No artifact tracking. Use this for ad-hoc automation, maintenance scripts, configuration management, etc.</p>

          <h3>Template type: Build</h3>
          <p>Use this for templates that <strong>produce an artifact</strong> — a compiled binary, a Docker image, a package, a deployment archive, etc.</p>
          <ul>
            <li>Each successful build task records a <strong>version number</strong> (stored on the task).</li>
            <li>The version is available to downstream deploy templates.</li>
            <li>Your script/playbook is responsible for the actual artifact creation. Oachkatzl tracks <em>which version was built when</em>.</li>
          </ul>

          <div class="callout example">
            <strong>Example build script (bash):</strong>
            <pre>#!/bin/bash
VERSION=$(git describe --tags --abbrev=0)
docker build -t myapp:$VERSION .
docker push myapp:$VERSION
echo "Built version $VERSION"</pre>
          </div>

          <h3>Template type: Deploy</h3>
          <p>Use this to <strong>deploy a specific build version</strong>. A deploy template references a <em>build template</em>.</p>
          <ul>
            <li>When starting a deploy task you select which build version to deploy.</li>
            <li>The deploy task stores a reference to the source build task (<code>build_task</code>).</li>
            <li>This gives you a clear audit trail: <em>"Production is running build #42, deployed at 14:32 by alice."</em></li>
          </ul>

          <div class="callout example">
            <strong>Example deploy script (bash):</strong>
            <pre>#!/bin/bash
# $OACHKATZL_BUILD_VERSION is injected from the build task
kubectl set image deployment/myapp myapp=myapp:$OACHKATZL_BUILD_VERSION
kubectl rollout status deployment/myapp</pre>
          </div>

          <h3>Typical workflow</h3>
          <ol>
            <li>Create a <strong>Build</strong> template → run it → artifact is created, version recorded.</li>
            <li>Create a <strong>Deploy</strong> template, referencing the build template.</li>
            <li>When you run the deploy, select the build version to deploy.</li>
            <li>Both tasks appear in the task history with their relationship visible.</li>
          </ol>
        </div>
      </section>

      <!-- ── Survey Variables ── -->
      <section id="survey">
        <h2 class="help-h2">Survey Variables</h2>
        <div class="prose-box">
          <p>Survey variables are <strong>prompted before each run</strong>, letting operators provide runtime values without editing the template.</p>

          <table class="help-table">
            <tr><th>Field type</th><th>UI</th><th>Notes</th></tr>
            <tr><td><strong>string</strong></td><td>Text input</td><td>Default type</td></tr>
            <tr><td><strong>int</strong></td><td>Number input</td><td>Validated as integer</td></tr>
            <tr><td><strong>enum</strong></td><td>Dropdown</td><td>Choices defined on the template</td></tr>
            <tr><td><strong>secret</strong></td><td>Password input</td><td>Value masked in UI, not stored in plain text logs</td></tr>
            <tr><td><strong>bool</strong></td><td>Checkbox</td><td>Passed as <code>true</code> / <code>false</code></td></tr>
            <tr><td><strong>separator</strong></td><td>Visual divider</td><td>Groups fields. Optional title. Not passed to the script.</td></tr>
          </table>

          <h3>How values are passed to scripts</h3>
          <ul>
            <li><strong>Ansible</strong> — added to <code>--extra-vars</code>. Access as <code v-pre>{{ var_name }}</code> in playbooks.</li>
            <li><strong>Bash</strong> — exported as environment variables. Access as <code>$var_name</code>.</li>
            <li><strong>Python</strong> — exported as environment variables. Access via <code>os.environ["var_name"]</code>.</li>
          </ul>

          <h3>Schedules with survey variables</h3>
          <p>When a template with survey variables is used in a schedule, the survey answers must be <strong>pre-configured on the schedule</strong>. If a required variable has no default and no schedule value, the run is skipped with an error in the worker log.</p>
        </div>
      </section>

      <!-- ── Tasks ── -->
      <section id="tasks">
        <h2 class="help-h2">Running Tasks</h2>
        <div class="prose-box">
          <h3>Task lifecycle</h3>
          <div class="flex items-center gap-2 flex-wrap text-sm my-3">
            <span class="badge gray">waiting</span>
            <span class="text-gray-400">→</span>
            <span class="badge blue">starting</span>
            <span class="text-gray-400">→</span>
            <span class="badge blue">running</span>
            <span class="text-gray-400">→</span>
            <span class="badge green">success</span>
            <span class="text-gray-300 text-xs">or</span>
            <span class="badge red">error</span>
            <span class="text-gray-300 text-xs">or</span>
            <span class="badge orange">stopped</span>
          </div>

          <h3>Run dialog options</h3>
          <table class="help-table">
            <tr><th>Option</th><th>Effect</th></tr>
            <tr><td>Survey answers</td><td>Fill in prompted variables before the run starts.</td></tr>
            <tr><td>Debug mode</td><td>Verbose output (ansible-playbook <code>-vvvv</code> + Oachkatzl internal logging).</td></tr>
            <tr><td>Dry run / Check</td><td>Ansible only: runs with <code>--check</code>. No changes are made to hosts.</td></tr>
            <tr><td>Diff</td><td>Ansible only: shows what would change (<code>--diff</code>).</td></tr>
            <tr><td>Override arguments</td><td>If the template allows it, append extra CLI arguments.</td></tr>
          </table>

          <h3>Stopping a task</h3>
          <p>Click <strong>Stop</strong> in the task detail or task list. Oachkatzl sends <code>SIGTERM</code> to the running process (checked every 500 ms). If the process does not exit within 10 seconds, <code>SIGKILL</code> is sent.</p>

          <h3>Log output</h3>
          <p>Output is polled from the backend every 1.5 seconds during the run and displayed with ANSI color support. The full log is archived in the database and available after the task completes.</p>

          <div class="callout info">
            <strong>Scheduled tasks</strong> show a purple <em>⏱ Scheduled</em> badge in the task list because they have no associated user.
          </div>
        </div>
      </section>

      <!-- ── Workflows ── -->
      <section id="workflows">
        <h2 class="help-h2">Workflows</h2>
        <div class="prose-box">
          <p>
            A <strong>Workflow</strong> chains multiple task templates into a directed graph.
            Each node runs one template; edges between nodes define when the next node starts
            based on the outcome of its predecessor.
          </p>

          <h3>Creating a workflow</h3>
          <p>
            Open a project, navigate to <em>Workflows</em> and click <strong>New workflow</strong>.
            The canvas opens with a <strong>START</strong> node. Hover over any node to reveal
            the toolbar, then use one of the four buttons to build the graph.
          </p>

          <h3>Node toolbar buttons</h3>
          <table class="help-table">
            <thead><tr><th>Button</th><th>What it does</th></tr></thead>
            <tbody>
              <tr>
                <td><span class="badge green">✓</span></td>
                <td><strong>Add on success</strong> — creates a new node connected with an <em>On Success</em> edge.</td>
              </tr>
              <tr>
                <td><span class="badge red">✗</span></td>
                <td><strong>Add on failure</strong> — creates a new node connected with an <em>On Failure</em> edge.</td>
              </tr>
              <tr>
                <td><span class="badge gray">→</span></td>
                <td><strong>Add always</strong> — creates a new node connected with an <em>Always</em> edge.</td>
              </tr>
              <tr>
                <td><span class="badge blue">🔗</span></td>
                <td><strong>Link to existing node</strong> — draws an edge from this node to any node already on the canvas. A dialog lets you choose the target and the condition. Use this to create <em>AND-joins</em> (multiple predecessors for one node).</td>
              </tr>
            </tbody>
          </table>

          <h3>Connection conditions</h3>
          <table class="help-table">
            <thead><tr><th>Condition</th><th>When the next node runs</th></tr></thead>
            <tbody>
              <tr><td><span class="badge green">✓ On Success</span></td><td>The predecessor task finished with exit code 0.</td></tr>
              <tr><td><span class="badge red">✗ On Failure</span></td><td>The predecessor task finished with a non-zero exit code or was stopped.</td></tr>
              <tr><td><span class="badge gray">→ Always</span></td><td>Regardless of the predecessor's outcome.</td></tr>
            </tbody>
          </table>

          <h3>Canvas controls</h3>
          <ul>
            <li><strong>Drag</strong> nodes to reposition them — positions are saved with the workflow.</li>
            <li><strong>Click</strong> a node to open the edit panel below the canvas (change label, template, or delete).</li>
            <li>Hover an edge and click <strong>×</strong> to remove the connection.</li>
            <li>The <strong>Auto-layout</strong> button (top-right of canvas) rearranges all nodes in columns by execution order and fits the viewport.</li>
          </ul>

          <h3>AND-join semantics</h3>
          <p>
            A node with <em>multiple predecessors</em> uses AND-join logic: it only starts once
            <strong>all</strong> predecessors have finished and at least one of their edges fires.
            If any predecessor votes "no" (its outcome does not match any outgoing edge type),
            the node is <strong>skipped</strong>.
          </p>
          <p>
            To create an AND-join, use the <strong>Link</strong> button (🔗) on each source node
            and point it to the shared target node. For example, to run a cleanup task only when
            both a "deploy" node and a "smoke-test" node have succeeded, link both to the cleanup
            node with an <em>On Success</em> edge.
          </p>

          <h3>Running a workflow</h3>
          <p>
            Click <strong>Run</strong> on the workflows list. If the workflow has
            <a @click.prevent="scrollTo('survey')" href="#" class="text-brand-600 hover:underline">survey variables</a>,
            they are collected once before the first node starts and passed to every node.
            The run view shows a live graph with per-node status badges and links to individual task logs.
          </p>

          <h3>Notifications</h3>
          <p>
            Individual task notifications are <strong>suppressed</strong> for tasks that run
            inside a workflow. A single summary notification is sent when the workflow run
            reaches a terminal state (<em>success</em> or <em>error</em>), respecting the
            <em>Suppress success alerts</em> setting on the workflow.
          </p>

          <div class="callout info">
            <strong>Tip:</strong> Use <em>On Failure</em> edges to build error-handling branches —
            for example, a rollback playbook that only runs when the deploy node fails.
          </div>
        </div>
      </section>

      <!-- ── Approval Gates ── -->
      <section id="approval-gate">
        <h2 class="help-h2">Approval Gates</h2>
        <div class="prose-box">
          <p>
            An <strong>Approval Gate</strong> is a special workflow node that <em>pauses</em> the entire workflow run
            and waits for a human decision before execution continues. When the gate is reached, a modal dialog
            appears in the run view with a question and two choices: <strong>Proceed</strong> or <strong>Cancel</strong>.
          </p>

          <div class="callout info">
            Approval Gates are only available inside <strong>Workflows</strong>. They have no associated template
            and do not consume a task slot — they are purely a coordination mechanism.
          </div>

          <h3>Adding an Approval Gate to a workflow</h3>
          <ol>
            <li>Open your workflow in the editor (<strong>Project → Workflows → Edit</strong>).</li>
            <li>Hover over any node to reveal the toolbar and click one of the condition buttons (✓ / ✗ / →).</li>
            <li>In the <em>Add node</em> dialog, click <strong>Approval Gate</strong> instead of Task.</li>
            <li>Enter a <strong>slug</strong> (e.g. <code>deploy-approval</code>) — this is the artifact name your preceding task must use. Also optionally enter a <strong>label</strong> for display on the canvas.</li>
            <li>Click <em>Add node</em>. The new node appears as an amber card with a <strong>?</strong> icon.</li>
          </ol>

          <h3>Visual appearance</h3>
          <table class="help-table">
            <thead><tr><th>State</th><th>Color / border</th><th>Status badge</th></tr></thead>
            <tbody>
              <tr><td>Editor (idle)</td><td>Amber background, amber border</td><td>—</td></tr>
              <tr><td>Run view — pending</td><td>Light slate</td><td>Pending</td></tr>
              <tr><td>Run view — waiting for input</td><td>Amber background, amber border (pulsing)</td><td>Approval</td></tr>
              <tr><td>Run view — approved</td><td>Green background</td><td>Success</td></tr>
              <tr><td>Run view — rejected</td><td>Orange background</td><td>Stopped</td></tr>
            </tbody>
          </table>

          <h3>What happens when the gate is reached</h3>
          <ol>
            <li>The workflow run status switches to <strong>Awaiting Approval</strong>.</li>
            <li>All users with at least the <code>task_runner</code> role can see the run and respond.</li>
            <li>A <strong>modal dialog</strong> appears automatically when the run view is open.</li>
            <li>The modal shows a title and optional description text (sourced from an artifact — see below). If no artifact is found, <em>"Proceed?"</em> is shown as the default.</li>
            <li>The user clicks <strong>Proceed</strong> or <strong>Cancel</strong>.</li>
          </ol>

          <h3>Outcomes</h3>
          <table class="help-table">
            <thead><tr><th>Decision</th><th>Gate node status</th><th>What happens next</th></tr></thead>
            <tbody>
              <tr>
                <td><strong>Proceed</strong></td>
                <td><span class="badge green">success</span></td>
                <td>
                  The workflow resumes. Downstream nodes connected with <em>On Success</em> or <em>Always</em>
                  edges are started; <em>On Failure</em> branches are skipped.
                </td>
              </tr>
              <tr>
                <td><strong>Cancel</strong></td>
                <td><span class="badge orange">stopped</span></td>
                <td>
                  The workflow is immediately stopped. All remaining <em>pending</em> nodes are marked as
                  <em>skipped</em>. No further tasks are executed.
                </td>
              </tr>
            </tbody>
          </table>

          <h3>Customising the approval question with an artifact</h3>
          <p>
            The gate reads its title and description text from a <strong>JSON artifact</strong> uploaded by
            the task that runs <em>immediately before</em> it. The artifact name must match the gate's
            <strong>slug</strong> — a short, human-readable identifier you define when creating the node.
          </p>

          <div class="callout info">
            <strong>Where to set the slug:</strong> When adding a node and selecting <em>Approval Gate</em>,
            fill in the <strong>Artifact slug</strong> field (e.g. <code>deploy-approval</code>). You can also
            change it later by clicking the node and editing the slug in the panel below the canvas.
            The slug is shown on the node card in small amber monospace text.
          </div>

          <p>The artifact must be uploaded as a <strong>JSON artifact</strong> with this structure:</p>
          <pre v-pre class="code-block">{
  "name": "&lt;slug&gt;",
  "data": {
    "title": "Deploy to production?",
    "text":  "This will push version 2.4.1 to all production nodes.\nMake sure the staging tests passed."
  }
}</pre>

          <h3>Example — Bash task before the gate</h3>
          <pre v-pre class="code-block">#!/bin/bash
# SLUG must match the "Artifact slug" set on the Approval Gate node in the editor
SLUG="deploy-approval"

TITLE="Deploy $APP_VERSION to production?"
TEXT="Staging tests: PASSED\nAffected hosts: web-01, web-02, web-03\nScheduled downtime: none"

curl -s -X POST "$OACHKATZL_ARTIFACT_URL" \
  -H "X-Artifact-Token: $OACHKATZL_ARTIFACT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$SLUG\", \"data\": {\"title\": \"$TITLE\", \"text\": \"$TEXT\"}}"</pre>

          <h3>Example — Python task before the gate</h3>
          <pre v-pre class="code-block">import os, requests

slug = "deploy-approval"   # must match the "Artifact slug" on the gate node

resp = requests.post(
    os.environ["OACHKATZL_ARTIFACT_URL"],
    headers={"X-Artifact-Token": os.environ["OACHKATZL_ARTIFACT_TOKEN"]},
    json={
        "name": slug,
        "data": {
            "title": f"Deploy {os.environ.get('APP_VERSION', '?')} to production?",
            "text":  "Staging smoke tests passed. Confirm production rollout.",
        },
    },
)
resp.raise_for_status()</pre>

          <div class="callout info">
            <strong>Artifact cache required:</strong> The workflow must have an <strong>Artifact Cache</strong>
            configured (Workflows editor → Artifact Cache dropdown) for the approval question text to be stored
            and retrieved. Without a cache, the gate still works but always shows the default <em>"Proceed?"</em>
            message.
          </div>

          <h3>Connecting gate outputs to downstream nodes</h3>
          <p>The gate node supports all three edge types:</p>
          <table class="help-table">
            <thead><tr><th>Edge condition</th><th>Fires when</th><th>Typical use</th></tr></thead>
            <tbody>
              <tr><td><span class="badge green">✓ On Success</span></td><td>User clicked <em>Proceed</em></td><td>Continue the happy path — deploy, notify, etc.</td></tr>
              <tr><td><span class="badge red">✗ On Failure</span></td><td>— (never — rejection sets the node to <em>stopped</em>, not error)</td><td>Not typically used</td></tr>
              <tr><td><span class="badge gray">→ Always</span></td><td>Either decision</td><td>Cleanup / audit logging regardless of outcome</td></tr>
            </tbody>
          </table>

          <div class="callout warning">
            <strong>Rejection terminates the run immediately.</strong>
            Unlike a failed task (which still propagates through <em>On Failure</em> edges), a rejected gate
            skips all remaining pending nodes and sets the run status to <em>stopped</em>. Design your workflow
            accordingly: add an <em>Always</em> edge if you need cleanup steps to run even after rejection.
          </div>

          <h3>Scheduling workflows with approval gates</h3>
          <p>
            Workflows containing approval gates can be scheduled, but consider whether an unattended schedule
            makes sense — the workflow will pause indefinitely at the gate until a user responds. If no one is
            monitoring the run view, the workflow will remain in <em>Awaiting Approval</em> status until action
            is taken.
          </p>
        </div>
      </section>

      <!-- ── Remote Approval Gate ── -->
      <section id="remote-approval-gate">
        <h2 class="help-h2">Remote Approval Gate</h2>
        <div class="prose-box">
          <p>
            A <strong>Remote Approval Gate</strong> is a workflow node that pauses execution and sends approval emails to a configurable list of recipients.
            Each recipient receives a personal email with two unique links — one to approve, one to reject — that work <strong>without logging in</strong>.
            Once one person makes a decision, all other links are automatically invalidated.
          </p>

          <div class="callout info">
            This differs from the regular <a @click.prevent="scrollTo('approval-gate')" href="#" class="text-brand-600 hover:underline">Approval Gate</a> in one key way:
            the in-app modal does not appear. The decision is made entirely via email, making it suitable for approvers who do not have an Oachkatzl account.
          </div>

          <h3>Adding a Remote Approval Gate</h3>
          <ol>
            <li>Open the workflow editor and hover over any node.</li>
            <li>Click a condition button (✓ / ✗ / →) to open the <em>Add node</em> dialog.</li>
            <li>Select <strong>Remote Approval</strong> (indigo button).</li>
            <li>Click <em>Add node</em>. The configuration dialog opens immediately.</li>
            <li>Optionally enter an <strong>Artifact slug</strong> (the name of a JSON artifact uploaded by the preceding task — provides title and text for the email).</li>
            <li>Add one or more <strong>recipient email addresses</strong>.</li>
            <li>Click <em>Save</em>. The node appears as an indigo card with a ✉ icon.</li>
          </ol>

          <h3>What happens when the node is reached</h3>
          <ol>
            <li>The workflow run switches to <strong>Awaiting Approval</strong> status.</li>
            <li>Each recipient receives an email with the approval title and text (from the artifact if configured) and two buttons: <strong>Approve</strong> and <strong>Reject</strong>.</li>
            <li>The workflow run view shows an info banner — no in-app modal appears.</li>
            <li>When a recipient clicks <em>Approve</em> or <em>Reject</em>, they are shown a confirmation page. The decision is recorded in the workflow run log.</li>
            <li>All other recipient links immediately become inactive. If clicked, they see a page stating who already decided and when.</li>
          </ol>

          <h3>Email content</h3>
          <p>The approval email is structured as follows:</p>
          <ul>
            <li><strong>Subject:</strong> <code>[Approval Required] &lt;title&gt;</code></li>
            <li><strong>Body:</strong> The artifact title and text, followed by an Approve button and a Reject button.</li>
            <li><strong>From:</strong> Configured <code>SMTP_FROM</code> address.</li>
          </ul>
          <p>The title and text come from a JSON artifact uploaded by the preceding task. The artifact name must match the node's <strong>Artifact slug</strong>:</p>
          <pre v-pre class="code-block">curl -s -X POST "$OACHKATZL_ARTIFACT_URL" \
  -H "X-Artifact-Token: $OACHKATZL_ARTIFACT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "deploy-approval", "data": {"title": "Deploy to production?", "text": "Version 2.4.1 — staging tests passed."}}'</pre>

          <h3>Approval links</h3>
          <p>Each link is a <code>GET</code> request to a public endpoint — no session or cookie is required:</p>
          <pre v-pre class="code-block">GET /api/remote-approval/&lt;token&gt;/approve
GET /api/remote-approval/&lt;token&gt;/reject
GET /api/remote-approval/&lt;token&gt;/status   ← shows current state with buttons if still pending</pre>
          <p>
            Each recipient gets their own unique token. Tokens are 256-bit URL-safe random strings and are single-use.
            The <code>/status</code> URL can be used to check the decision state and still act if no decision has been made yet.
          </p>

          <h3>Outcomes</h3>
          <table class="help-table">
            <thead><tr><th>Decision</th><th>Node status</th><th>What happens</th></tr></thead>
            <tbody>
              <tr>
                <td><strong>Approve</strong></td>
                <td><span class="badge green">success</span></td>
                <td>Workflow resumes. Downstream <em>On Success</em> / <em>Always</em> edges fire.</td>
              </tr>
              <tr>
                <td><strong>Reject</strong></td>
                <td><span class="badge orange">stopped</span></td>
                <td>Workflow stops immediately. All pending nodes are skipped. A workflow completion notification is sent.</td>
              </tr>
            </tbody>
          </table>

          <h3>Audit log</h3>
          <p>
            Every decision is logged in the project's activity log with the email address of the person who decided and the timestamp.
            The decision is also visible on the workflow run node list.
          </p>

          <h3>Requirements</h3>
          <ul>
            <li>SMTP must be configured under <strong>Admin → Settings</strong>.</li>
            <li>The workflow must have a reachable <code>OACHKATZL_BASE_URL</code> (set in the environment) so the approval links resolve from outside the Docker network.</li>
            <li>An <a @click.prevent="scrollTo('artifacts')" href="#" class="text-brand-600 hover:underline">Artifact Cache</a> must be attached to the workflow if you want to provide a custom title/text via artifact.</li>
          </ul>

          <div class="callout warning">
            The approve / reject links work <strong>without authentication</strong>. Treat them like passwords — anyone who receives the email (or a forwarded copy of it) can make the decision. Do not use this feature for high-security decisions where non-repudiation is required.
          </div>
        </div>
      </section>

      <!-- ── Action Nodes ── -->
      <section id="action-nodes">
        <h2 class="help-h2">Action Nodes</h2>
        <div class="prose-box">
          <p>
            <strong>Action Nodes</strong> are special workflow nodes that perform built-in operations
            on <a @click.prevent="scrollTo('artifacts')" href="#" class="text-brand-600 hover:underline">Artifact Cache</a> data —
            without running a script or playbook. They are added the same way as task nodes: hover over any
            node on the canvas, click a condition button (✓ / ✗ / →), then choose <em>Action Node</em> in the
            <em>Add node</em> dialog.
          </p>

          <div class="callout info">
            <strong>Source artifact:</strong> All action nodes consume an artifact produced by an earlier node.
            The <strong>Source artifact tag</strong> is set once in the <em>Add node</em> dialog and identifies
            the artifact by name. The workflow must have an <strong>Artifact Cache</strong> configured for action
            nodes to read from.
          </div>

          <h3>Available action node types</h3>
          <table class="help-table">
            <thead><tr><th>Type</th><th>What it does</th></tr></thead>
            <tbody>
              <tr><td><strong>List Generator</strong></td><td>Converts a JSON array artifact to a downloadable XLSX or CSV file and stores it back in the artifact cache.</td></tr>
              <tr><td><strong>PDF Generator</strong></td><td>Renders a Markdown or HTML artifact as a PDF and stores the result in the artifact cache.</td></tr>
              <tr><td><strong>Send Mail</strong></td><td>Sends an email, optionally attaching an artifact file.</td></tr>
              <tr><td><strong>Transfer File</strong></td><td>Uploads an artifact file to a remote server via SFTP or SMB.</td></tr>
            </tbody>
          </table>

          <!-- List Generator -->
          <h3>List Generator</h3>
          <p>
            Reads a <strong>JSON array</strong> artifact (a list of objects) and converts it to an
            <strong>XLSX</strong> or <strong>CSV</strong> file. The generated file is uploaded back to
            the artifact cache under the configured output filename and is immediately downloadable from the UI.
          </p>
          <p>
            The source artifact must be a JSON artifact whose top-level value is an array of objects.
            The object keys become column headers in the spreadsheet.
          </p>

          <table class="help-table">
            <thead><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td>Source artifact tag</td><td>yes</td><td>Name of the JSON array artifact to convert. Set in the <em>Add node</em> dialog.</td></tr>
              <tr><td>Output format</td><td>yes</td><td><code>XLSX</code> (default) or <code>CSV</code>.</td></tr>
              <tr><td>Output filename</td><td>no</td><td>Name for the generated file (e.g. <code>report.xlsx</code>). Defaults to <code>output.xlsx</code> / <code>output.csv</code>.</td></tr>
            </tbody>
          </table>

          <p>Example — uploading a list artifact from Bash for the List Generator to process:</p>
          <pre v-pre class="code-block">#!/bin/bash
PAYLOAD=$(jq -n '[
  {"host":"web-01","status":"ok","changed":3},
  {"host":"web-02","status":"ok","changed":1},
  {"host":"db-01","status":"failed","changed":0}
]')
curl -s -X POST "$OACHKATZL_ARTIFACT_URL" \
  -H "X-Artifact-Token: $OACHKATZL_ARTIFACT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"host-results\", \"data\": $PAYLOAD}"</pre>
          <p>Set <em>Source artifact tag</em> to <code>host-results</code> on the List Generator node. The node produces <code>report.xlsx</code> in the cache.</p>

          <!-- PDF Generator -->
          <h3>PDF Generator</h3>
          <p>
            Reads a <strong>Markdown</strong> (<code>.md</code>) or <strong>HTML</strong> artifact,
            renders it as a PDF (A4 portrait, 2 cm margins), and stores the result in the artifact cache.
            Markdown is converted to HTML before rendering. Jinja2 templating is applied if a
            <code>data</code> JSON artifact with the same run token is present.
          </p>

          <table class="help-table">
            <thead><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td>Source artifact tag</td><td>yes</td><td>Name of the Markdown or HTML artifact to render. Set in the <em>Add node</em> dialog.</td></tr>
              <tr><td>Output filename</td><td>no</td><td>Name for the generated PDF (e.g. <code>report.pdf</code>). Defaults to <code>output.pdf</code>.</td></tr>
            </tbody>
          </table>

          <p>Example — uploading a Markdown template from Python:</p>
          <pre v-pre class="code-block">import os, requests

token = os.environ["OACHKATZL_ARTIFACT_TOKEN"]
url   = os.environ["OACHKATZL_ARTIFACT_URL"]

md = """# Deployment Report

| Host   | Status |
|--------|--------|
| web-01 | OK     |
| web-02 | OK     |
"""

# Upload as a file with a .md extension
headers = {"X-Artifact-Token": token}
resp = requests.post(url, headers=headers,
                     files={"file": ("report.md", md.encode(), "text/markdown")},
                     data={"name": "report.md"})
resp.raise_for_status()</pre>
          <p>Set <em>Source artifact tag</em> to <code>report.md</code> on the PDF Generator node.</p>

          <!-- Send Mail -->
          <h3>Send Mail</h3>
          <p>
            Sends an email via the configured SMTP server (see
            <a @click.prevent="scrollTo('notifications')" href="#" class="text-brand-600 hover:underline">Notifications → SMTP configuration</a>).
            An artifact file can optionally be attached to the email.
          </p>

          <table class="help-table">
            <thead><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td>Attachment artifact tag</td><td>no</td><td>Name of the artifact to attach. Set in the <em>Add node</em> dialog. Leave blank for no attachment.</td></tr>
              <tr><td>To</td><td>yes</td><td>One or more recipient email addresses.</td></tr>
              <tr><td>Subject</td><td>yes</td><td>Email subject line.</td></tr>
              <tr><td>Body</td><td>no</td><td>Plain-text email body.</td></tr>
            </tbody>
          </table>

          <div class="callout info">
            SMTP must be configured under <strong>Settings</strong> before Send Mail nodes can deliver email.
            A test SMTP server (Mailpit) is included in the Docker Compose setup and reachable at <code>http://localhost:8026</code>.
          </div>

          <!-- Transfer File -->
          <h3>Transfer File</h3>
          <p>
            Uploads an artifact file to a remote server using <strong>SFTP</strong> or <strong>SMB</strong>.
            The remote path supports dynamic tokens that are resolved at run time.
          </p>

          <table class="help-table">
            <thead><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td>Source artifact tag</td><td>yes</td><td>Name of the artifact file to upload. Set in the <em>Add node</em> dialog.</td></tr>
              <tr><td>Protocol</td><td>yes</td><td><code>SFTP</code> (default) or <code>SMB</code>.</td></tr>
              <tr><td>Credential</td><td>yes</td><td>A Custom Credential that supplies the connection details (host, username, password / key).</td></tr>
              <tr><td>Remote path</td><td>yes</td><td>Destination path on the remote server. Supports path tokens (see below).</td></tr>
            </tbody>
          </table>

          <h3>Remote path tokens</h3>
          <p>Click any token chip in the Remote Path field to insert it. Tokens are resolved at run time:</p>
          <table class="help-table">
            <thead><tr><th>Token</th><th>Resolves to</th></tr></thead>
            <tbody>
              <tr><td><code>{date}</code></td><td><code>YYYY-MM-DD</code></td></tr>
              <tr><td><code>{datetime}</code></td><td><code>YYYY-MM-DDTHH-MM-SS</code></td></tr>
              <tr><td><code>{year}</code></td><td>4-digit year</td></tr>
              <tr><td><code>{month}</code></td><td>2-digit month</td></tr>
              <tr><td><code>{day}</code></td><td>2-digit day</td></tr>
              <tr><td><code>{workflow_run_id}</code></td><td>MongoDB ObjectId of the workflow run</td></tr>
              <tr><td><code>{workflow_name}</code></td><td>Name of the workflow</td></tr>
              <tr><td><code>{node_name}</code></td><td>Label of this action node</td></tr>
            </tbody>
          </table>

          <p>Example path: <code>/reports/{year}/{month}/report-{date}.xlsx</code> → <code>/reports/2026/06/report-2026-06-18.xlsx</code></p>

          <h3>Setting up the Credential Type for Transfer File</h3>
          <p>
            The Transfer File node uses a <a @click.prevent="scrollTo('custom-creds')" href="#" class="text-brand-600 hover:underline">Custom Credential</a>
            to supply connection details. You must create the Credential Type once (admin only) and then create Credentials for each target server.
          </p>

          <h4 style="font-size:.85rem;font-weight:600;color:#374151;margin-top:.75rem">SFTP Credential Type</h4>
          <p><strong>Inputs schema:</strong></p>
          <pre v-pre class="code-block">[
  { "id": "host",     "label": "Host",     "type": "string",  "required": true  },
  { "id": "port",     "label": "Port",     "type": "string",  "required": false, "default": "22" },
  { "id": "username", "label": "Username", "type": "string",  "required": true  },
  { "id": "password", "label": "Password", "type": "secret",  "required": false },
  { "id": "key",      "label": "SSH Private Key", "type": "secret", "required": false,
    "help_text": "PEM-encoded private key. Leave blank to use password auth." }
]</pre>
          <p><strong>Injectors schema:</strong></p>
          <pre v-pre class="code-block">{
  "env": {
    "SFTP_HOST":     "{{ host }}",
    "SFTP_PORT":     "{{ port }}",
    "SFTP_USERNAME": "{{ username }}",
    "SFTP_PASSWORD": "{{ password }}",
    "SFTP_KEY":      "{{ key }}"
  }
}</pre>

          <h4 style="font-size:.85rem;font-weight:600;color:#374151;margin-top:.75rem">SMB Credential Type</h4>
          <p><strong>Inputs schema:</strong></p>
          <pre v-pre class="code-block">[
  { "id": "host",     "label": "Host / Server",  "type": "string", "required": true  },
  { "id": "share",    "label": "Share Name",      "type": "string", "required": true  },
  { "id": "username", "label": "Username",        "type": "string", "required": true  },
  { "id": "password", "label": "Password",        "type": "secret", "required": true  },
  { "id": "domain",   "label": "Domain (optional)", "type": "string", "required": false }
]</pre>
          <p><strong>Injectors schema:</strong></p>
          <pre v-pre class="code-block">{
  "env": {
    "SMB_HOST":     "{{ host }}",
    "SMB_SHARE":    "{{ share }}",
    "SMB_USERNAME": "{{ username }}",
    "SMB_PASSWORD": "{{ password }}",
    "SMB_DOMAIN":   "{{ domain }}"
  }
}</pre>

          <div class="callout info">
            After creating the Credential Type under <strong>Settings → Credential Types</strong>, create a Credential
            of that type in your project under <strong>Keys &amp; Credentials → Credentials</strong>.
            The Transfer File node's <em>Credential</em> picker lists all project credentials — select the one that matches the target server.
          </div>
        </div>
      </section>

      <!-- ── Artifact Cache ── -->
      <section id="artifacts">
        <h2 class="help-h2">Artifact Cache</h2>
        <div class="prose-box">
          <p>
            An <strong>Artifact Cache</strong> lets tasks persistently store files and JSON data during execution
            and retrieve them later — from the same task, a downstream workflow node, or the project UI.
            Each task run gets an injected <strong>token</strong> that authenticates all upload and list calls.
          </p>

          <h3>Setup</h3>
          <ol>
            <li>Open your project and navigate to <strong>Artifact Caches</strong> in the sidebar.</li>
            <li>Click <em>New cache</em>, give it a name and a retention period (0 = never expire).</li>
            <li>Open a template or workflow, scroll to the <strong>Artifact Cache</strong> section and select the cache.</li>
          </ol>

          <h3>Injected environment variables</h3>
          <p>When a task starts and its template (or workflow) has a cache configured, Oachkatzl injects five variables into the subprocess environment:</p>
          <table class="help-table">
            <thead><tr><th>Variable</th><th>Reaches</th><th>Use when</th></tr></thead>
            <tbody>
              <tr><td><code>OACHKATZL_ARTIFACT_TOKEN</code></td><td colspan="2">Auth token for upload / list calls (scoped to this run).</td></tr>
              <tr><td><code>OACHKATZL_ARTIFACT_URL</code></td><td>Internal Docker network (<code>http://api:5000</code>)</td><td>Script runs <em>inside</em> a Docker task (Bash, Python, Ansible on localhost).</td></tr>
              <tr><td><code>OACHKATZL_ARTIFACT_LIST_URL</code></td><td>Internal Docker network</td><td>Same — listing artifacts from within the worker.</td></tr>
              <tr><td><code>OACHKATZL_ARTIFACT_URL_EXT</code></td><td>External URL (<code>OACHKATZL_BASE_URL</code>)</td><td>Passing the URL to a remote host or an external system.</td></tr>
              <tr><td><code>OACHKATZL_ARTIFACT_LIST_URL_EXT</code></td><td>External URL</td><td>Same — listing from an external system.</td></tr>
            </tbody>
          </table>
          <div class="callout info">
            <strong>Which URL to use?</strong>
            Scripts that run directly on the worker container (Bash, Python, Ansible with <code>hosts: localhost</code>) should use <code>OACHKATZL_ARTIFACT_URL</code> — it goes directly to the API container over the Docker network, bypassing nginx.
            Use <code>OACHKATZL_ARTIFACT_URL_EXT</code> only when you need to reach the API from a remote machine (e.g., passing the URL as an extra-var to an Ansible play that runs on an external host).
          </div>

          <div class="callout info">
            <strong>Workflows:</strong> All nodes in a workflow share the <em>same token</em>. A downstream node can therefore read artifacts uploaded by an earlier node without any extra configuration.
          </div>

          <h3>Uploading a file — Shell / Bash</h3>
          <pre v-pre class="code-block">#!/bin/bash
# Upload a binary or text file
curl -s -X POST "$OACHKATZL_ARTIFACT_URL" \
  -H "X-Artifact-Token: $OACHKATZL_ARTIFACT_TOKEN" \
  -F "name=report.tar.gz" \
  -F "file=@/tmp/report.tar.gz"

# Upload a plain-text log
curl -s -X POST "$OACHKATZL_ARTIFACT_URL" \
  -H "X-Artifact-Token: $OACHKATZL_ARTIFACT_TOKEN" \
  -F "name=output.log" \
  -F "file=@/var/log/myapp.log"</pre>

          <h3>Uploading JSON — Shell / Bash</h3>
          <pre v-pre class="code-block">#!/bin/bash
# Upload a JSON object (any valid JSON value)
curl -s -X POST "$OACHKATZL_ARTIFACT_URL" \
  -H "X-Artifact-Token: $OACHKATZL_ARTIFACT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "results.json", "data": {"hosts_ok": 5, "hosts_failed": 0}}'

# Upload a JSON array (downloadable as CSV from the UI)
PAYLOAD=$(jq -n '[
  {"host":"web-01","status":"ok","changed":3},
  {"host":"web-02","status":"ok","changed":1}
]')
curl -s -X POST "$OACHKATZL_ARTIFACT_URL" \
  -H "X-Artifact-Token: $OACHKATZL_ARTIFACT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"hosts.json\", \"data\": $PAYLOAD}"</pre>

          <h3>Listing artifacts — Shell</h3>
          <pre v-pre class="code-block">#!/bin/bash
# Returns a JSON array of all artifacts in the current run
curl -s "$OACHKATZL_ARTIFACT_LIST_URL" \
  -H "X-Artifact-Token: $OACHKATZL_ARTIFACT_TOKEN" | jq .

# Example output:
# [
#   {"id": "abc123", "name": "results.json", "artifact_type": "json", "size_bytes": 82, ...},
#   {"id": "def456", "name": "report.tar.gz", "artifact_type": "file", "size_bytes": 14302, ...}
# ]</pre>

          <h3>Downloading an artifact in a downstream task — Shell</h3>
          <pre v-pre class="code-block">#!/bin/bash
# Step 1: find the artifact by name
AID=$(curl -s "$OACHKATZL_ARTIFACT_LIST_URL" \
  -H "X-Artifact-Token: $OACHKATZL_ARTIFACT_TOKEN" \
  | jq -r '.[] | select(.name=="results.json") | .id')

# Step 2: derive download URL from list URL
BASE=$(echo "$OACHKATZL_ARTIFACT_LIST_URL" | sed 's|/list$||')

# Step 3: download the file
curl -s "$BASE/$AID/download" \
  -H "X-Artifact-Token: $OACHKATZL_ARTIFACT_TOKEN" \
  -o /tmp/results.json

cat /tmp/results.json</pre>

          <h3>Uploading a file — Python</h3>
          <pre v-pre class="code-block">import os, requests

token = os.environ["OACHKATZL_ARTIFACT_TOKEN"]
url   = os.environ["OACHKATZL_ARTIFACT_URL"]

# File upload — do NOT set Content-Type here.
# requests sets "multipart/form-data; boundary=..." automatically.
# If Content-Type is already present in headers, requests will NOT override it,
# and the server will reject the request with 400.
file_headers = {"X-Artifact-Token": token}

with open("/tmp/report.tar.gz", "rb") as f:
    resp = requests.post(url, headers=file_headers,
                         files={"file": f},
                         data={"name": "report.tar.gz"})
    resp.raise_for_status()
    print("Uploaded:", resp.json())</pre>

          <h3>Uploading JSON — Python</h3>
          <pre v-pre class="code-block">import os, requests

token = os.environ["OACHKATZL_ARTIFACT_TOKEN"]
url   = os.environ["OACHKATZL_ARTIFACT_URL"]

# JSON upload — use requests' json= parameter, which sets Content-Type automatically.
# Alternatively pass headers={"X-Artifact-Token": token, "Content-Type": "application/json"}
# and body=json.dumps(...) — but the json= shortcut is simpler and less error-prone.
json_headers = {"X-Artifact-Token": token}

data = {
    "name": "scan_results.json",
    "data": [
        {"host": "web-01", "open_ports": [22, 80, 443]},
        {"host": "db-01",  "open_ports": [22, 5432]},
    ]
}
resp = requests.post(url, headers=json_headers, json=data)
resp.raise_for_status()
print("Artifact ID:", resp.json()["id"])</pre>

          <h3>Reading artifacts in a downstream task — Python</h3>
          <pre v-pre class="code-block">import os, requests

token    = os.environ["OACHKATZL_ARTIFACT_TOKEN"]
list_url = os.environ["OACHKATZL_ARTIFACT_LIST_URL"]
headers  = {"X-Artifact-Token": token}

# List all artifacts in this run (includes those from earlier nodes)
artifacts = requests.get(list_url, headers=headers).json()

# Find and download a specific artifact
for art in artifacts:
    if art["name"] == "scan_results.json":
        base = list_url.replace("/list", "")
        content = requests.get(f"{base}/{art['id']}/download",
                               headers=headers).json()
        print(content)
        break</pre>

          <h3>Uploading a file — Ansible</h3>
          <p>Use the <code>uri</code> module to call the artifact API from within a playbook. The injected environment variables are available via <code>ansible.builtin.shell</code> or directly as Jinja2 lookups.</p>
          <pre v-pre class="code-block">---
- name: Upload artifact from Ansible
  hosts: localhost
  gather_facts: false
  tasks:

    # 1. Read injected variables from the worker environment
    - name: Get artifact vars
      ansible.builtin.set_fact:
        artifact_token: "{{ lookup('env', 'OACHKATZL_ARTIFACT_TOKEN') }}"
        artifact_url:   "{{ lookup('env', 'OACHKATZL_ARTIFACT_URL') }}"

    # 2. Upload a JSON report
    #    Important: do NOT set Content-Type in headers when using body_format: json.
    #    body_format: json sets it automatically AND handles serialisation.
    #    Adding Content-Type manually can prevent Ansible from serialising the body,
    #    causing the server to receive a raw Python dict string instead of valid JSON.
    - name: Upload JSON report
      ansible.builtin.uri:
        url: "{{ artifact_url }}"
        method: POST
        headers:
          X-Artifact-Token: "{{ artifact_token }}"
        body_format: json
        body:
          name: "ansible_report.json"
          data:
            play: "{{ ansible_play_name }}"
            hosts_ok: "{{ ansible_stats.ok | default({}) | length }}"
        status_code: [200, 201]
      register: upload_result

    - name: Show artifact ID
      ansible.builtin.debug:
        msg: "Stored with ID {{ upload_result.json.id }}"

    # 3. Upload a file (e.g., a generated archive)
    - name: Upload tar archive
      ansible.builtin.shell: |
        curl -s -X POST "{{ artifact_url }}" \
          -H "X-Artifact-Token: {{ artifact_token }}" \
          -F "name=backup.tar.gz" \
          -F "file=@/tmp/backup.tar.gz"</pre>

          <h3>Reading artifacts from an earlier node — Ansible</h3>
          <pre v-pre class="code-block">---
- name: Download artifact uploaded by a previous workflow node
  hosts: localhost
  gather_facts: false
  tasks:

    - name: Get artifact vars
      ansible.builtin.set_fact:
        artifact_token:    "{{ lookup('env', 'OACHKATZL_ARTIFACT_TOKEN') }}"
        artifact_list_url: "{{ lookup('env', 'OACHKATZL_ARTIFACT_LIST_URL') }}"

    - name: List artifacts
      ansible.builtin.uri:
        url: "{{ artifact_list_url }}"
        method: GET
        headers:
          X-Artifact-Token: "{{ artifact_token }}"
        return_content: true
      register: artifact_list

    - name: Find scan_results.json
      ansible.builtin.set_fact:
        scan_artifact: >-
          {{ artifact_list.json
             | selectattr('name', 'equalto', 'scan_results.json')
             | first }}

    - name: Download artifact
      ansible.builtin.uri:
        url: "{{ artifact_list_url | regex_replace('/list$', '') }}/{{ scan_artifact.id }}/download"
        method: GET
        headers:
          X-Artifact-Token: "{{ artifact_token }}"
        return_content: true
      register: scan_data

    - name: Show scan results
      ansible.builtin.debug:
        var: scan_data.json</pre>

          <h3>Viewing and downloading artifacts in the UI</h3>
          <ul>
            <li>Open a task and switch to the <strong>Artifacts</strong> tab to see all artifacts for that run.</li>
            <li>Files download directly. JSON artifacts can be downloaded as <em>native JSON</em> or as <em>CSV</em> (a list-of-objects structure is automatically converted with headers).</li>
            <li>Browse all runs for a cache under <strong>Project → Artifact Caches</strong>.</li>
          </ul>

          <h3>Upload API reference</h3>
          <table class="help-table">
            <thead><tr><th>Field</th><th>Type</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td colspan="3" class="text-xs text-gray-400 font-semibold uppercase bg-gray-50">File upload — multipart/form-data</td></tr>
              <tr><td><code>name</code></td><td>string (required)</td><td>Artifact display name (e.g. <code>report.tar.gz</code>).</td></tr>
              <tr><td><code>file</code></td><td>file (required)</td><td>The file to upload. Content-Type is detected automatically.</td></tr>
              <tr><td colspan="3" class="text-xs text-gray-400 font-semibold uppercase bg-gray-50">JSON upload — application/json body</td></tr>
              <tr><td><code>name</code></td><td>string (required)</td><td>Artifact display name (e.g. <code>results.json</code>).</td></tr>
              <tr><td><code>data</code></td><td>any JSON (required)</td><td>The JSON value to store. A top-level array of objects enables CSV export.</td></tr>
            </tbody>
          </table>

          <div class="callout warning">
            <strong>Token scope:</strong> The artifact token is scoped to a single run. It cannot be used to read or write artifacts from other runs or other caches. The token expires with the run's retention period.
          </div>
        </div>
      </section>

      <!-- ── pip Package Proxy ── -->
      <section id="pip-proxy">
        <h2 class="help-h2">pip Package Proxy</h2>
        <div class="prose-box">
          <p>
            By default pip downloads packages from PyPI on every Python task run. A <strong>caching proxy</strong>
            (devpi or any PEP 503-compatible server) eliminates repeat downloads: packages are fetched once
            and served locally on all subsequent runs — including runs on other workers.
          </p>

          <h3>How it works</h3>
          <p>Set <code>OACHKATZL_PIP_INDEX_URL</code> on the worker. Oachkatzl passes it as <code>--index-url</code>
          to every <code>pip install</code> invocation. For HTTP-only proxies the required <code>--trusted-host</code>
          flag is added automatically.</p>

          <div class="callout info">
            <strong>Automatic fallback:</strong> If the proxy is unreachable or pip exits with an error,
            Oachkatzl immediately retries the install directly against PyPI. Tasks never fail solely because
            the proxy is down or temporarily unavailable.
          </div>

          <h3>Docker Compose setup (included)</h3>
          <p>Both <code>docker-compose.yml</code> and <code>docker-compose.hub.yml</code> include a
          pre-configured <strong>devpi</strong> service. The worker is already wired to use it — no manual
          configuration needed for a single-node setup.</p>

          <table class="help-table">
            <thead><tr><th>Service / Port</th><th>Purpose</th></tr></thead>
            <tbody>
              <tr><td><code>devpi</code> — port <code>3141</code></td><td>Caching pip proxy, reachable inside Docker as <code>http://devpi:3141</code> and from the host as <code>http://&lt;host&gt;:3141</code>.</td></tr>
              <tr><td><code>pip_cache</code> volume</td><td>pip HTTP cache mounted into the worker at <code>/root/.cache/pip</code> — speeds up even the proxy-miss case.</td></tr>
            </tbody>
          </table>

          <h3>Distributed / remote workers</h3>
          <p>
            Workers outside the Docker network set <code>OACHKATZL_PIP_INDEX_URL</code> to the external
            devpi URL. Workers that cannot reach devpi simply leave the variable unset and use PyPI directly.
          </p>
          <pre v-pre class="code-block"># .env on a remote worker — point to the devpi instance on the main host
OACHKATZL_PIP_INDEX_URL=http://10.62.4.5:3141/root/pypi/+simple/</pre>

          <h3>Using a different proxy</h3>
          <p>Any PEP 503-compatible index works — Nexus Repository, Artifactory, pypiserver, etc.:</p>
          <pre v-pre class="code-block"># Nexus / Artifactory
OACHKATZL_PIP_INDEX_URL=https://nexus.example.com/repository/pypi-proxy/simple/

# pypiserver (self-hosted, no caching — serves pre-downloaded packages)
OACHKATZL_PIP_INDEX_URL=http://pypiserver.example.com/simple/</pre>

          <h3>Environment variable reference</h3>
          <table class="help-table">
            <thead><tr><th>Variable</th><th>Default</th><th>Description</th></tr></thead>
            <tbody>
              <tr>
                <td><code>OACHKATZL_PIP_INDEX_URL</code></td>
                <td><em>empty</em></td>
                <td>pip <code>--index-url</code>. Empty = PyPI. HTTP URLs get <code>--trusted-host</code> added automatically.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- ── Scaling Workers ── -->
      <section id="scaling">
        <h2 class="help-h2">Scaling Workers</h2>
        <div class="prose-box">
          <p>Tasks are executed by <strong>Celery workers</strong>. By default the Docker Compose setup starts a single worker with a concurrency of 4 (4 parallel task slots). You can scale this in two ways:</p>

          <h3>Option 1 — Increase concurrency of a single worker</h3>
          <p>Set the <code>WORKER_CONCURRENCY</code> environment variable on the worker service and rebuild:</p>
          <pre v-pre class="code-block">worker:
  environment:
    WORKER_CONCURRENCY: 8   # default: 4</pre>
          <p>This is the simplest option and works well if your tasks are I/O-bound (waiting for SSH connections, API calls, etc.).</p>

          <h3>Option 2 — Spawn additional worker containers</h3>
          <p>Use <code>docker compose up --scale</code> to run multiple worker replicas:</p>
          <pre v-pre class="code-block"># Start 3 worker containers (each with its own concurrency)
docker compose up -d --scale worker=3</pre>

          <p>You can also add the <code>deploy.replicas</code> setting permanently in your <code>docker-compose.yml</code>:</p>
          <pre v-pre class="code-block">worker:
  # ... existing config ...
  deploy:
    replicas: 3</pre>

          <div class="callout info">
            All worker replicas share the same Redis task queue and MongoDB database — no additional configuration is needed. Tasks are distributed automatically by Celery across all available workers.
          </div>

          <h3>Per-template parallelism</h3>
          <p>By default, tasks from the same template run <strong>sequentially</strong> — a Redis lock prevents a second run while one is already in progress. To allow concurrent runs of the same template, enable <strong>Allow parallel tasks</strong> on the template.</p>

          <h3>Beat (scheduler) — do not scale</h3>
          <p>The <code>beat</code> service (Celery Beat) must run as a <strong>single instance only</strong>. Running multiple Beat replicas causes duplicate task submissions. Always keep <code>replicas: 1</code> for the beat service.</p>

          <h3>Checking worker status</h3>
          <pre v-pre class="code-block"># List active workers and their queues
docker compose exec worker celery -A app.celery_app inspect active

# Monitor via Flower (if enabled)
# http://localhost:5555</pre>
        </div>
      </section>

      <!-- ── Custom Workers ── -->
      <section id="custom-workers">
        <h2 class="help-h2">Custom Workers</h2>
        <div class="prose-box">
          <p>
            A <strong>Worker Pool</strong> is a named Celery queue that a dedicated worker container listens to.
            Custom worker images — with additional binaries, GPU drivers, specific Python packages, or restricted network access —
            register themselves by setting a single environment variable. Templates and Custom Apps can then target that pool,
            so only the matching worker executes those tasks.
          </p>

          <div class="callout info">
            The default worker listens to the built-in <code>celery</code> queue.
            All templates that have no pool assigned continue to run there as before.
            Custom pools are completely opt-in and additive.
          </div>

          <h3>Step 1 — Define a Worker Pool (Admin)</h3>
          <p>
            Go to <strong>Settings → Worker Pools</strong> in the sidebar and click <em>New pool</em>.
            The <strong>slug</strong> is the Celery queue name — it must match exactly what the worker container advertises.
          </p>

          <table class="help-table">
            <thead><tr><th>Field</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td><code>slug</code></td><td>Celery queue name. Lowercase letters, digits, <code>-</code> and <code>_</code>. Immutable after creation. Example: <code>gpu</code>, <code>ansible-extended</code>.</td></tr>
              <tr><td><code>name</code></td><td>Human-readable display name shown in dropdowns.</td></tr>
              <tr><td><code>description</code></td><td>Optional — what this pool is for, what tools it provides.</td></tr>
              <tr><td><code>active</code></td><td>Inactive pools are hidden from dropdowns but existing assignments are preserved.</td></tr>
            </tbody>
          </table>

          <h3>Step 2 — Start a worker that consumes the pool</h3>
          <p>
            Tell the worker which queue to consume via the <code>OACHKATZL_WORKER_QUEUES</code> environment variable.
            The variable is passed directly to Celery's <code>-Q</code> flag.
          </p>

          <pre v-pre class="code-block"># docker-compose.yml — add a second worker service
worker-gpu:
  image: my-gpu-worker:latest      # custom image with CUDA, tensorflow, etc.
  command: >-
    sh -c "celery -A worker.celery worker -l info -c 2 -Q $$OACHKATZL_WORKER_QUEUES"
  env_file: .env
  environment:
    OACHKATZL_WORKER_QUEUES: "gpu"
    OACHKATZL_PIP_INDEX_URL: "http://devpi:3141/root/pypi/+simple/"
  depends_on:
    mongo: { condition: service_healthy }
    redis: { condition: service_healthy }
  volumes:
    - /tmp/oachkatzl:/tmp/oachkatzl</pre>

          <p>
            The container can be any image that includes the Oachkatzl backend code and the additional tools you need.
            Use the official worker image as a base and layer your dependencies on top:
          </p>

          <pre v-pre class="code-block"># Dockerfile.worker-gpu
FROM lanbugsde/oachkatzl-worker:latest

# Install extra system packages
RUN apt-get update && apt-get install -y terraform kubectl && rm -rf /var/lib/apt/lists/*

# Install extra Python packages
RUN pip install boto3 kubernetes</pre>

          <div class="callout info">
            <strong>Multiple queues on one worker:</strong> Set a comma-separated list to consume several queues at once —
            e.g. <code>OACHKATZL_WORKER_QUEUES=gpu,default</code>. This is useful for a "catch-all" secondary worker
            that handles both custom and default tasks.
          </div>

          <h3>Step 3 — Assign a pool to a Template</h3>
          <p>
            Open the template editor. If at least one Worker Pool exists, a <strong>Worker pool</strong> dropdown appears
            in the <em>Basic info</em> section. Select the pool; the hint below the dropdown shows the queue name
            the worker must listen to.
          </p>
          <p>Leave it at <em>Default worker</em> to keep using the standard <code>celery</code> queue.</p>

          <h3>Step 4 — Assign a pool to a Custom App (optional)</h3>
          <p>
            In <strong>Settings → Custom Apps</strong>, each app can have a <strong>default worker pool</strong>.
            This pool applies automatically to every template that uses this app type — unless the template overrides it
            with its own pool selection.
          </p>
          <p>
            Use this to guarantee, for example, that the <code>terraform</code> custom app always runs on a worker
            that has Terraform installed, without requiring every template author to remember to set the pool.
          </p>

          <h3>Pool resolution order</h3>
          <p>When a task is enqueued, the target queue is resolved in this priority order:</p>
          <ol>
            <li><strong>Template's worker pool</strong> — set directly on the template (highest priority).</li>
            <li><strong>Custom App's worker pool</strong> — the default pool of the app type used by the template.</li>
            <li><strong>Default queue</strong> (<code>celery</code>) — if neither template nor app specifies a pool.</li>
          </ol>

          <h3>Environment variable reference</h3>
          <table class="help-table">
            <thead><tr><th>Variable</th><th>Set on</th><th>Description</th></tr></thead>
            <tbody>
              <tr>
                <td><code>OACHKATZL_WORKER_QUEUES</code></td>
                <td>Worker container</td>
                <td>Comma-separated list of Celery queue names this worker consumes. Default: <code>celery</code>. Must match the <em>slug</em> of the Worker Pool defined in the UI.</td>
              </tr>
            </tbody>
          </table>

          <h3>Verifying the setup</h3>
          <pre v-pre class="code-block"># List active workers and the queues they are listening to
docker compose exec worker celery -A worker.celery inspect active_queues

# Inspect the custom worker container
docker compose exec worker-gpu celery -A worker.celery inspect active_queues</pre>

          <p>
            Create a template, assign it to your custom pool, and trigger a task.
            The task should appear in the log of the custom worker container — not the default one.
          </p>

          <div class="callout warning">
            <strong>No worker running for a pool?</strong> If a task is enqueued to a queue that no worker is consuming,
            it remains in <code>waiting</code> status indefinitely. Oachkatzl does not currently detect this automatically.
            Always ensure at least one worker is started for every active pool that templates use.
          </div>

          <h3>Practical example — Terraform runner</h3>
          <p>Goal: run Terraform plans and applies on a dedicated worker with the correct binary and cloud credentials pre-installed.</p>

          <ol>
            <li>Create a Worker Pool: slug <code>terraform</code>, name <em>Terraform Worker</em>.</li>
            <li>Build a custom image with <code>terraform</code> in <code>/usr/local/bin</code>.</li>
            <li>Add a <code>worker-terraform</code> service in <code>docker-compose.yml</code> with <code>OACHKATZL_WORKER_QUEUES=terraform</code>.</li>
            <li>Register a Custom App: slug <code>terraform</code>, executable <code>/usr/local/bin/terraform</code>, default pool → <em>Terraform Worker</em>.</li>
            <li>Create templates using app type <em>terraform</em> — they automatically target the Terraform worker. No per-template pool selection needed.</li>
          </ol>
        </div>
      </section>

      <!-- ── Custom Apps ── -->
      <section id="custom-apps">
        <h2 class="help-h2">Custom Apps</h2>
        <div class="prose-box">
          <p>
            <strong>Custom Apps</strong> extend the built-in app types (<em>Ansible</em>, <em>Bash</em>, <em>Python</em>)
            with any executable available in the worker image — Terraform, kubectl, make, a custom binary, or anything
            else reachable in the worker's <code>PATH</code>. Once registered, a Custom App appears as an additional
            app type in the template editor, just like the built-in types.
          </p>

          <div class="callout info">
            Creating and editing Custom Apps is restricted to <strong>global admins</strong>.
            Project members can use an active app in templates but cannot modify its definition.
          </div>

          <h3>Creating a Custom App</h3>
          <p>Go to <strong>Settings → Custom Apps</strong> in the sidebar and click <em>New app</em>.</p>

          <table class="help-table">
            <thead><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
            <tbody>
              <tr>
                <td><code>slug</code></td><td>yes</td>
                <td>
                  Unique identifier — lowercase letters, digits, <code>-</code> and <code>_</code>.
                  This becomes the <code>app</code> value stored on templates. Immutable after creation.
                  Example: <code>terraform</code>, <code>kubectl</code>, <code>make</code>.
                </td>
              </tr>
              <tr>
                <td>Title</td><td>yes</td>
                <td>Human-readable name shown in the app-type dropdown in the template editor.</td>
              </tr>
              <tr>
                <td>Executable</td><td>yes</td>
                <td>
                  Binary name (looked up in <code>PATH</code>) or absolute path on the worker.
                  Examples: <code>terraform</code>, <code>/usr/local/bin/kubectl</code>.
                </td>
              </tr>
              <tr>
                <td>Default arguments</td><td>no</td>
                <td>
                  JSON array of arguments <em>always</em> prepended to every invocation — before
                  the script file and template arguments.
                  Example: <code>["--no-color"]</code> for Terraform.
                </td>
              </tr>
              <tr>
                <td>Args template</td><td>no</td>
                <td>
                  Controls how the command line is assembled. Two placeholders are available:
                  <code>{file}</code> (the script/playbook path from the template) and
                  <code>{arguments}</code> (the template's Arguments field).
                  Default: <code>{file} {arguments}</code>.
                </td>
              </tr>
              <tr>
                <td>Worker pool</td><td>no</td>
                <td>
                  Default <a @click.prevent="scrollTo('custom-workers')" href="#" class="text-brand-600 hover:underline">Worker Pool</a>
                  for this app type. Applied to all templates that use this app unless the template overrides it.
                  Useful to ensure, e.g., that <code>terraform</code> always runs on a worker with Terraform installed.
                </td>
              </tr>
              <tr>
                <td>Active</td><td>—</td>
                <td>Inactive apps are hidden from the template editor. Existing templates using the app are not affected.</td>
              </tr>
            </tbody>
          </table>

          <h3>How the command is assembled</h3>
          <p>For each task run, Oachkatzl builds the subprocess command in this order:</p>
          <ol>
            <li><strong>Executable</strong> — the binary.</li>
            <li><strong>Default arguments</strong> — always present, from the app definition.</li>
            <li><strong>Script file and/or template arguments</strong> — controlled by the <em>Args template</em>.</li>
          </ol>

          <table class="help-table">
            <thead><tr><th>Args template</th><th>Resulting command</th></tr></thead>
            <tbody>
              <tr>
                <td><code>{file} {arguments}</code> (default)</td>
                <td><code>executable [default_args] script.tf --var env=prod</code></td>
              </tr>
              <tr>
                <td><code>{arguments}</code></td>
                <td><code>executable [default_args] --var env=prod</code> — no script file passed</td>
              </tr>
              <tr>
                <td><code>{file}</code></td>
                <td><code>executable [default_args] script.tf</code> — no extra arguments</td>
              </tr>
              <tr>
                <td>(empty / anything else)</td>
                <td><code>executable [default_args] script.tf [arguments]</code> — same as default</td>
              </tr>
            </tbody>
          </table>

          <div class="callout warning">
            <strong>Security:</strong> Custom Apps execute arbitrary binaries on the worker. Only global admins can
            register or modify them. The binary must already be present in the worker image — Oachkatzl never
            downloads or installs executables at run time. Arguments are always passed as a list
            (no shell interpolation), so shell injection via template arguments is not possible.
          </div>

          <h3>Example — Terraform</h3>
          <p><strong>App definition:</strong></p>
          <table class="help-table">
            <tr><td>Slug</td><td><code>terraform</code></td></tr>
            <tr><td>Title</td><td>Terraform</td></tr>
            <tr><td>Executable</td><td><code>terraform</code></td></tr>
            <tr><td>Default arguments</td><td><code>["-no-color"]</code></td></tr>
            <tr><td>Args template</td><td><code>{arguments}</code> (Terraform subcommands are passed as arguments, not as a script file)</td></tr>
            <tr><td>Worker pool</td><td><em>Terraform Worker</em> (a pool whose worker image includes the Terraform binary)</td></tr>
          </table>

          <p><strong>Template using this app:</strong></p>
          <ul>
            <li>App type: <em>terraform</em></li>
            <li>Script / playbook: leave blank (Args template has no <code>{file}</code>)</li>
            <li>Arguments: <code>["apply", "-auto-approve", "-var", "env=production"]</code></li>
          </ul>
          <p>Resulting command: <code>terraform -no-color apply -auto-approve -var env=production</code></p>

          <h3>Example — kubectl</h3>
          <table class="help-table">
            <tr><td>Slug</td><td><code>kubectl</code></td></tr>
            <tr><td>Executable</td><td><code>/usr/local/bin/kubectl</code></td></tr>
            <tr><td>Default arguments</td><td><code>[]</code></td></tr>
            <tr><td>Args template</td><td><code>{arguments}</code></td></tr>
          </table>
          <p>Template Arguments: <code>["rollout", "restart", "deployment/myapp", "-n", "production"]</code></p>
          <p>Resulting command: <code>/usr/local/bin/kubectl rollout restart deployment/myapp -n production</code></p>

          <h3>Using a Custom App in a template</h3>
          <ol>
            <li>Open a template (new or existing) and scroll to <strong>App type</strong>.</li>
            <li>Select the Custom App from the dropdown — it appears alongside Ansible, Bash, Python.</li>
            <li>Fill in the <strong>Script / playbook</strong> field if the args template uses <code>{file}</code>; leave blank otherwise.</li>
            <li>Add any run-time arguments in the <strong>Arguments</strong> field (JSON array).</li>
            <li>Environment variables, Survey Variables, Repositories, and Artifact Cache all work the same as with built-in app types.</li>
          </ol>

          <div class="callout info">
            Inventory and Vault are Ansible-specific and have no effect on Custom App templates.
          </div>
        </div>
      </section>

      <!-- ── Schedules ── -->
      <section id="schedules">
        <h2 class="help-h2">Schedules</h2>
        <div class="prose-box">
          <p>Schedules trigger templates automatically using a cron expression. They are evaluated by <strong>Celery Beat</strong> every minute.</p>

          <h3>Cron format</h3>
          <p>Standard 5-field cron: <code>minute hour day month weekday</code></p>
          <table class="help-table">
            <tr><th>Expression</th><th>Meaning</th></tr>
            <tr><td><code>0 * * * *</code></td><td>Every hour</td></tr>
            <tr><td><code>0 8 * * 1-5</code></td><td>08:00 on weekdays</td></tr>
            <tr><td><code>*/15 * * * *</code></td><td>Every 15 minutes</td></tr>
            <tr><td><code>0 0 1 * *</code></td><td>First day of every month at midnight</td></tr>
          </table>
          <p>Use <a href="https://crontab.guru" target="_blank" class="text-brand-600 hover:underline">crontab.guru</a> to validate expressions.</p>

          <h3>Survey variables on schedules</h3>
          <p>Pre-configure survey answers directly on the schedule. At run time the stored values are used. The caller can also pass <code>survey_answers</code> via the execute token API.</p>
        </div>
      </section>

      <!-- ── Execute Tokens ── -->
      <section id="tokens">
        <h2 class="help-h2">Execute Tokens</h2>
        <div class="prose-box">
          <p>Execute tokens let external systems trigger a specific template <strong>without full API authentication</strong>. The token is the only credential — treat it like a password.</p>

          <h3>Creating a token</h3>
          <ol>
            <li>Open the template list and click the 🔑 icon on a template.</li>
            <li>Click <strong>Generate token</strong>.</li>
            <li>Give it a name (e.g. "CI pipeline"), optionally set an expiry date.</li>
            <li>If the template has survey variables, pre-fill defaults for this token.</li>
            <li>Copy the token — it is shown <strong>only once</strong>.</li>
          </ol>

          <h3>Triggering a run</h3>
          <pre v-pre class="code-block"># Simple trigger
curl -X POST "https://oachkatzl.example.com/api/execute/&lt;token&gt;"

# With survey variable overrides
curl -X POST "https://oachkatzl.example.com/api/execute/&lt;token&gt;" \
  -H "Content-Type: application/json" \
  -d '{"survey_answers": {"env": "production", "version": "2.1.0"}}'</pre>

          <p>The response contains the <code>task_id</code> which can be used to poll the task status:</p>
          <pre v-pre class="code-block">GET /api/projects/&lt;project_id&gt;/tasks/&lt;task_id&gt;</pre>

          <h3>Survey answer precedence</h3>
          <ol>
            <li>Values in the request body <code>survey_answers</code> (highest priority)</li>
            <li>Token default values</li>
            <li>Template survey variable defaults</li>
          </ol>

          <div class="callout warning">
            Tokens cannot be retrieved after creation. If lost, revoke the old token and generate a new one.
          </div>
        </div>
      </section>

      <!-- ── Notifications ── -->
      <section id="notifications">
        <h2 class="help-h2">Notifications</h2>
        <div class="prose-box">
          <p>Notification rules fire when a task completes. Rules can be scoped to a project or set globally by an admin.</p>

          <table class="help-table">
            <tr><th>Channel</th><th>Configuration</th></tr>
            <tr><td>Slack</td><td>Incoming Webhook URL</td></tr>
            <tr><td>E-Mail</td><td>Recipient selection (all members / specific members / custom addresses). Requires SMTP configured under <strong>Settings</strong>.</td></tr>
            <tr><td>Telegram</td><td>Bot token + Chat ID</td></tr>
            <tr><td>Microsoft Teams</td><td>Incoming Webhook URL</td></tr>
            <tr><td>Gotify</td><td>Server URL + App token</td></tr>
          </table>

          <h3>Email recipients</h3>
          <ul>
            <li><strong>All members</strong> — every project member's registered email address.</li>
            <li><strong>Specific members</strong> — select individual members from the list.</li>
            <li><strong>Extra addresses only</strong> — custom email addresses (useful for external recipients).</li>
          </ul>
          <p>Extra addresses are always appended regardless of the member mode.</p>

          <h3>Suppress success alerts</h3>
          <p>Enable this on the template to only receive notifications for <em>failed</em> runs, even if a notification rule has "on success" enabled.</p>

          <h3>SMTP configuration</h3>
          <p>Configure in <strong>Settings</strong> in the sidebar:</p>
          <table class="help-table">
            <tr><th>Key</th><th>Example</th></tr>
            <tr><td>SMTP_HOST</td><td><code>smtp.gmail.com</code></td></tr>
            <tr><td>SMTP_PORT</td><td><code>587</code></td></tr>
            <tr><td>SMTP_TLS</td><td><code>true</code></td></tr>
            <tr><td>SMTP_USER</td><td><code>user@gmail.com</code></td></tr>
            <tr><td>SMTP_PASSWORD</td><td>App password</td></tr>
            <tr><td>SMTP_FROM</td><td><code>oachkatzl@example.com</code></td></tr>
          </table>
          <p>A test SMTP server (Mailpit) is included in the Docker Compose setup for development. Access it at <code>http://localhost:8026</code>.</p>
        </div>
      </section>

      <!-- ── 2FA & Security ── -->
      <section id="2fa">
        <h2 class="help-h2">2FA &amp; Security</h2>
        <div class="prose-box">
          <h3>Two-factor authentication (TOTP)</h3>
          <p>Oachkatzl supports TOTP (RFC 6238) compatible with any authenticator app (Google Authenticator, Authy, 1Password, etc.).</p>
          <ol>
            <li>Go to your profile or use the API: <code>GET /api/auth/2fa/setup</code> to get a QR code.</li>
            <li>Scan the QR code with your authenticator app.</li>
            <li>Confirm with a 6-digit code: <code>POST /api/auth/2fa/enable</code>.</li>
            <li>Save the recovery codes — they can bypass 2FA if you lose your device.</li>
          </ol>

          <h3>Recovery codes</h3>
          <p>8 single-use codes are generated when 2FA is enabled. Store them safely. Each code can only be used once.</p>

          <h3>API tokens vs 2FA</h3>
          <p>API tokens (from <em>Profile → API Tokens</em>) bypass the interactive 2FA step — the token itself is the secret. This makes them suitable for automation. Tokens can be revoked at any time.</p>

          <h3>Secret storage</h3>
          <ul>
            <li>All credentials (SSH keys, passwords, vault passwords, TOTP secrets) are stored encrypted with <strong>Fernet (AES-128-CBC)</strong>.</li>
            <li>Passwords use <strong>argon2id</strong> hashing.</li>
            <li>The encryption key (<code>OACHKATZL_ENCRYPTION_KEY</code>) must be set in the environment and is never stored in the database.</li>
            <li>Subprocess environments are sanitized — internal secrets are never visible to playbooks or scripts.</li>
          </ul>

          <div class="callout warning">
            <strong>Production checklist:</strong>
            Generate a fresh <code>OACHKATZL_ENCRYPTION_KEY</code> (<code>python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"</code>),
            set a strong <code>OACHKATZL_JWT_SECRET</code>, and change <code>OACHKATZL_ADMIN_PASSWORD</code> before going live.
          </div>
        </div>
      </section>

      <!-- ── Profile ── -->
      <section id="profile">
        <h2 class="help-h2">Profile</h2>
        <div class="prose-box">
          <p>Access your profile via the user icon in the bottom-left of the sidebar or navigate to <strong>/profile</strong>. The page is divided into three cards.</p>

          <h3>Profile info</h3>
          <p>Shows your username, email address, global role (User / Administrator) and authentication provider (local, ldap, oidc). These fields are read-only and can only be changed by an admin.</p>

          <h3>Change password</h3>
          <p>Only visible for <strong>local accounts</strong>. Users authenticated via LDAP or OIDC manage their password through the external provider — the card is replaced by an informational notice.</p>
          <ol>
            <li>Enter your current password.</li>
            <li>Enter and confirm the new password (minimum 8 characters).</li>
            <li>Click <strong>Change password</strong>.</li>
          </ol>

          <h3>Two-Factor Authentication</h3>
          <p>Enable or disable TOTP-based 2FA for your account here. See the <a @click.prevent="scrollTo('2fa')" href="#" class="text-brand-600 hover:underline">2FA &amp; Security</a> section for the full enrollment flow.</p>
          <p>
            If your administrator has enforced 2FA globally, you will see a banner on the profile page and be redirected here until 2FA is set up.
            You cannot dismiss this banner or use any other part of the app until enrollment is complete.
          </p>

          <h3>API Tokens</h3>
          <p>
            API tokens allow scripts and CI/CD pipelines to authenticate with the REST API without interactive login or 2FA.
            They are managed via the API itself — there is currently no UI form for this:
          </p>
          <pre v-pre class="code-block"># List your tokens
GET /api/auth/tokens

# Create a new token
POST /api/auth/tokens
{"name": "ci-pipeline", "expires_at": null}
# → returns {"token": "eyJ...", "id": "..."}  — copy the token now, it won't be shown again

# Revoke a token
DELETE /api/auth/tokens/&lt;token_id&gt;</pre>
          <p>Tokens bypass the interactive 2FA step — the token itself is the credential. Revoke tokens immediately if they are compromised. Tokens can optionally carry an expiry date (<code>expires_at</code> in ISO 8601 format).</p>
        </div>
      </section>

      <!-- ── Admin: User Management ── -->
      <section id="admin-users">
        <h2 class="help-h2">Admin: User Management</h2>
        <div class="prose-box">
          <p>Global admins manage all users under <strong>Admin → Users</strong> in the sidebar. Regular users do not see this page.</p>

          <h3>Creating a user</h3>
          <p>Click <strong>New user</strong> and fill in the form:</p>
          <table class="help-table">
            <thead><tr><th>Field</th><th>Required</th><th>Notes</th></tr></thead>
            <tbody>
              <tr><td>Username</td><td>yes</td><td>Unique, used for login. Cannot be changed after creation.</td></tr>
              <tr><td>Email</td><td>yes</td><td>Used for notifications and display.</td></tr>
              <tr><td>Name</td><td>no</td><td>Display name shown next to the username.</td></tr>
              <tr><td>Password</td><td>yes</td><td>Minimum 8 characters. The user can change it later on their profile page.</td></tr>
              <tr><td>Global admin</td><td>no</td><td>Grants access to all projects and the Admin section.</td></tr>
            </tbody>
          </table>

          <h3>Editing a user</h3>
          <p>Click the edit icon on any user row. Editable fields:</p>
          <ul>
            <li><strong>Email</strong> and <strong>Name</strong> — update display and notification address.</li>
            <li><strong>New password</strong> — leave blank to keep the current password. Useful for admin password reset.</li>
            <li><strong>Global admin</strong> — toggle admin status.</li>
            <li><strong>Active</strong> — deactivating a user blocks all logins without deleting the account. Existing task runs and audit entries are preserved.</li>
          </ul>

          <h3>User list indicators</h3>
          <table class="help-table">
            <thead><tr><th>Badge</th><th>Meaning</th></tr></thead>
            <tbody>
              <tr><td><span class="badge blue">admin</span> (shield icon)</td><td>User has global admin privileges.</td></tr>
              <tr><td><span class="badge red">inactive</span></td><td>Account is deactivated — login is blocked.</td></tr>
              <tr><td><span class="badge green">2FA</span></td><td>User has TOTP two-factor authentication enabled.</td></tr>
            </tbody>
          </table>

          <div class="callout info">
            <strong>LDAP users:</strong> Users who log in via LDAP are created automatically on first login. Their username, email, and display name are synced from the directory. You can still set the <em>admin</em> flag manually or via LDAP admin group mappings.
          </div>
        </div>
      </section>

      <!-- ── Admin: Global Settings ── -->
      <section id="admin-settings">
        <h2 class="help-h2">Admin: Global Settings</h2>
        <div class="prose-box">
          <p>Accessible via <strong>Admin → Settings</strong> in the sidebar. Changes take effect immediately without a restart.</p>

          <h3>Two-Factor Authentication (MFA)</h3>
          <p>The <strong>Require MFA for all users</strong> toggle forces every user to enroll in TOTP before they can use the application. Users who have not yet set up 2FA are redirected to the profile page on their next login and cannot proceed until enrollment is complete.</p>

          <h3>Task History Retention</h3>
          <p>Controls how long completed task records (log output, status, run metadata) are kept in the database. Options: <em>Disabled</em> (keep forever), 7 days, 30 days, 90 days, 1 year. Tasks older than the threshold are deleted by a background cleanup job. Running tasks are never deleted.</p>

          <h3>SMTP / E-Mail</h3>
          <p>See <a @click.prevent="scrollTo('notifications')" href="#" class="text-brand-600 hover:underline">Notifications → SMTP configuration</a>.</p>

          <h3>LDAP / Active Directory</h3>
          <p>Oachkatzl can authenticate users against an LDAP or Active Directory server. On successful login, group memberships are read and synced to project roles automatically via group-to-project mappings.</p>

          <table class="help-table">
            <thead><tr><th>Field</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td>Enabled</td><td>Toggle LDAP authentication on or off. Local accounts continue to work regardless.</td></tr>
              <tr><td>Server URL</td><td>LDAP server address including scheme and port. Examples: <code>ldap://dc.example.com:389</code>, <code>ldaps://dc.example.com:636</code>.</td></tr>
              <tr><td>Use TLS / Use SSL</td><td>Enable STARTTLS (port 389) or LDAPS (port 636). Use only one at a time.</td></tr>
              <tr><td>Bind DN</td><td>Service account DN used to search the directory. Example: <code>CN=svc-oachkatzl,OU=ServiceAccounts,DC=example,DC=com</code>.</td></tr>
              <tr><td>Bind password</td><td>Password for the bind account. Stored encrypted. Leave blank when editing to keep the existing password.</td></tr>
              <tr><td>Base DN</td><td>Root of the directory tree to search. Example: <code>DC=example,DC=com</code>.</td></tr>
              <tr><td>User search filter</td><td>LDAP filter to find a user by login name. Default: <code>(sAMAccountName={username})</code>. For OpenLDAP use <code>(uid={username})</code>.</td></tr>
              <tr><td>Group membership attribute</td><td>Attribute on the user object that lists group memberships. Default: <code>memberOf</code>.</td></tr>
              <tr><td>Follow nested groups</td><td>Resolve nested group memberships (recursive). Can be slow on large directories.</td></tr>
              <tr><td>Email attribute</td><td>LDAP attribute mapped to the user's email. Default: <code>mail</code>.</td></tr>
              <tr><td>Display name attribute</td><td>LDAP attribute mapped to the user's display name. Default: <code>displayName</code>.</td></tr>
              <tr><td>UID attribute</td><td>Stable unique identifier for the user (used to link LDAP users to existing accounts). Default: <code>objectGUID</code>.</td></tr>
              <tr><td>Admin groups</td><td>List of group DNs whose members automatically receive global admin privileges in Oachkatzl.</td></tr>
            </tbody>
          </table>

          <h3>Testing the LDAP connection</h3>
          <p>After saving the configuration, click <strong>Test connection</strong>. Oachkatzl attempts a bind with the configured service account and returns a success or error message. A successful test confirms network connectivity and credentials — it does not test user login or group mapping.</p>

          <h3>Group-to-project mappings</h3>
          <p>
            Map LDAP/AD groups to project roles. When a user logs in, Oachkatzl reads their group memberships and automatically adds them to the configured projects with the mapped role. Users are also removed from projects if they leave the group.
          </p>
          <table class="help-table">
            <thead><tr><th>Field</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td>Group DN</td><td>Full distinguished name of the LDAP group. Example: <code>CN=Ops-Team,OU=Groups,DC=example,DC=com</code>.</td></tr>
              <tr><td>Project</td><td>The Oachkatzl project to assign membership in.</td></tr>
              <tr><td>Role</td><td>The project role to assign (owner / manager / task_runner / guest).</td></tr>
            </tbody>
          </table>

          <div class="callout info">
            Members added via LDAP group mapping are shown with an <span class="badge blue" style="font-size:10px">LDAP</span> badge in the project Members view. Their role is re-applied on each login, so manual changes may be overwritten.
          </div>
        </div>
      </section>

      <!-- About -->
      <section id="about">
        <h2 class="help-h2">About</h2>
        <div class="prose-box">
          <p>Oachkatzl is an open-source automation orchestration platform — a self-hosted alternative to Semaphore UI / Ansible AWX.</p>
          <div class="mt-6 bg-white rounded-xl border border-gray-200 p-6 space-y-4">
            <div class="flex items-center gap-3">
              <img src="@/assets/logo.svg" alt="Oachkatzl" class="w-10 h-10 rounded-xl" />
              <div>
                <p class="font-semibold text-gray-900">Oachkatzl</p>
                <p class="text-xs text-gray-400">by Maximilian Thoma 2026</p>
              </div>
            </div>
            <div class="border-t border-gray-100 pt-4 space-y-2">
              <a href="https://lanbugs.de" target="_blank" rel="noopener"
                class="flex items-center gap-2 text-sm text-brand-600 hover:text-brand-800 transition-colors">
                <span class="w-4 text-center">🌐</span> lanbugs.de
              </a>
              <a href="https://netdevops.blog" target="_blank" rel="noopener"
                class="flex items-center gap-2 text-sm text-brand-600 hover:text-brand-800 transition-colors">
                <span class="w-4 text-center">📝</span> netdevops.blog
              </a>
              <a href="https://github.com/lanbugs/oachkatzl" target="_blank" rel="noopener"
                class="flex items-center gap-2 text-sm text-brand-600 hover:text-brand-800 transition-colors">
                <span class="w-4 text-center">⚙️</span> github.com/lanbugs/oachkatzl
              </a>
            </div>
          </div>

          <!-- License -->
          <div class="mt-4 bg-gray-50 rounded-xl border border-gray-200 p-5 space-y-2">
            <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">License</p>
            <p class="text-sm text-gray-700">
              Oachkatzl is released under the
              <a href="https://opensource.org/licenses/MIT" target="_blank" rel="noopener"
                class="text-brand-600 hover:text-brand-800 underline underline-offset-2">MIT License</a>.
              You are free to use, modify and distribute this software.
            </p>
            <p class="text-xs text-gray-400 pt-1">
              Third-party dependencies are licensed under their respective terms.
              Notable: <code class="bg-gray-200 px-1 rounded">ldap3</code> is LGPL-3.0 — used as a dynamically linked library and replaceable by the user.
            </p>
          </div>
        </div>
      </section>

    </div>
  </div>
</template>

<style scoped>
.help-h2 {
  @apply text-2xl font-bold text-gray-900 mb-4 pt-2;
}
.prose-box {
  @apply text-gray-700 space-y-4 text-sm leading-relaxed;
}
.prose-box h3 {
  @apply text-base font-semibold text-gray-900 mt-5 mb-2;
}
.prose-box ul, .prose-box ol {
  @apply pl-5 space-y-1;
}
.prose-box ul { @apply list-disc; }
.prose-box ol { @apply list-decimal; }
.prose-box p code, .prose-box li code {
  @apply bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-xs font-mono;
}
.help-table {
  @apply w-full text-sm border-collapse;
}
.help-table th {
  @apply text-left text-xs font-semibold text-gray-500 uppercase tracking-wide bg-gray-50 px-3 py-2 border border-gray-200;
}
.help-table td {
  @apply px-3 py-2 border border-gray-200 align-top;
}
.help-table tr:hover td { @apply bg-gray-50; }
.code-block {
  @apply bg-gray-900 text-gray-200 rounded-xl px-4 py-3 text-xs font-mono overflow-x-auto whitespace-pre;
}
.callout {
  @apply rounded-xl px-4 py-3 text-sm border;
}
.callout.info    { @apply bg-blue-50 border-blue-200 text-blue-800; }
.callout.warning { @apply bg-amber-50 border-amber-200 text-amber-800; }
.callout.example { @apply bg-gray-50 border-gray-200 text-gray-700; }
.callout pre     { @apply mt-2 text-xs font-mono bg-gray-900 text-gray-200 rounded-lg px-3 py-2 overflow-x-auto whitespace-pre; }
.badge {
  @apply text-xs font-medium px-2 py-0.5 rounded-full;
}
.badge.purple { @apply bg-purple-100 text-purple-700; }
.badge.blue   { @apply bg-blue-100 text-blue-700; }
.badge.green  { @apply bg-green-100 text-green-700; }
.badge.gray   { @apply bg-gray-100 text-gray-600; }
.badge.red    { @apply bg-red-100 text-red-700; }
.badge.orange { @apply bg-orange-100 text-orange-700; }
</style>
