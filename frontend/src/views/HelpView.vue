<script setup lang="ts">
import { ref } from 'vue'

const sections = [
  { id: 'overview',       label: 'Overview' },
  { id: 'projects',       label: 'Projects & Roles' },
  { id: 'keys',           label: 'Access Keys' },
  { id: 'custom-creds',   label: 'Custom Credentials' },
  { id: 'repositories',   label: 'Repositories' },
  { id: 'inventories',    label: 'Inventories' },
  { id: 'environments',   label: 'Environments & Variables' },
  { id: 'templates',      label: 'Templates' },
  { id: 'build-deploy',   label: 'Build & Deploy' },
  { id: 'survey',         label: 'Survey Variables' },
  { id: 'tasks',          label: 'Running Tasks' },
  { id: 'scaling',        label: 'Scaling Workers' },
  { id: 'schedules',      label: 'Schedules' },
  { id: 'tokens',         label: 'Execute Tokens' },
  { id: 'notifications',  label: 'Notifications' },
  { id: '2fa',            label: '2FA & Security' },
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
          <p>Open <strong>Credential Types</strong> in the left sidebar (visible to admins only) and click <em>New type</em>. Each type has two JSON fields:</p>

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
            <li>Runs <code>pip install -r requirements.txt</code></li>
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

      <!-- ── Scaling Workers ── -->
      <section id="scaling">
        <h2 class="help-h2">Scaling Workers</h2>
        <div class="prose-box">
          <p>Tasks are executed by <strong>Celery workers</strong>. By default the Docker Compose setup starts a single worker with a concurrency of 4 (4 parallel task slots). You can scale this in two ways:</p>

          <h3>Option 1 — Increase concurrency of a single worker</h3>
          <p>Set the <code>WORKER_CONCURRENCY</code> environment variable on the worker service and rebuild:</p>
          <pre class="code-block">worker:
  environment:
    WORKER_CONCURRENCY: 8   # default: 4</pre>
          <p>This is the simplest option and works well if your tasks are I/O-bound (waiting for SSH connections, API calls, etc.).</p>

          <h3>Option 2 — Spawn additional worker containers</h3>
          <p>Use <code>docker compose up --scale</code> to run multiple worker replicas:</p>
          <pre class="code-block"># Start 3 worker containers (each with its own concurrency)
docker compose up -d --scale worker=3</pre>

          <p>You can also add the <code>deploy.replicas</code> setting permanently in your <code>docker-compose.yml</code>:</p>
          <pre class="code-block">worker:
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
          <pre class="code-block"># List active workers and their queues
docker compose exec worker celery -A app.celery_app inspect active

# Monitor via Flower (if enabled)
# http://localhost:5555</pre>
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
          <pre class="code-block"># Simple trigger
curl -X POST "https://oachkatzl.example.com/api/execute/&lt;token&gt;"

# With survey variable overrides
curl -X POST "https://oachkatzl.example.com/api/execute/&lt;token&gt;" \
  -H "Content-Type: application/json" \
  -d '{"survey_answers": {"env": "production", "version": "2.1.0"}}'</pre>

          <p>The response contains the <code>task_id</code> which can be used to poll the task status:</p>
          <pre class="code-block">GET /api/projects/&lt;project_id&gt;/tasks/&lt;task_id&gt;</pre>

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
            <tr><td>E-Mail</td><td>Recipient selection (all members / specific members / custom addresses). Requires SMTP in Admin → Settings.</td></tr>
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
          <p>Configure in <strong>Admin → Settings</strong>:</p>
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
                <p class="text-xs text-gray-400">Written by Maximilian Thoma &copy; 2026</p>
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
