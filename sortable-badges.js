// This is free and unencumbered software released into the public domain.
// See the UNLICENSE file for details.

// Thanks to Claude AI for the batch-based loading
// approach to stay within GitHub's request rate limit.

function addTokenUI() {
    const controlDiv = document.createElement('div');
    controlDiv.style.position = 'fixed';
    controlDiv.style.top = '10px';
    controlDiv.style.left = '10px';
    controlDiv.style.background = '#f0f0f0';
    controlDiv.style.padding = '10px';
    controlDiv.style.borderRadius = '5px';
    controlDiv.style.border = '1px solid #ccc';

    const tokenInput = document.createElement('input');
    tokenInput.type = 'password';
    tokenInput.placeholder = 'GitHub token (workflow read only)';
    tokenInput.style.marginRight = '10px';

    const loadButton = document.createElement('button');
    loadButton.textContent = 'Load Build Status';

    const progress = document.createElement('div');
    progress.style.marginTop = '5px';
    progress.style.fontSize = '12px';

    controlDiv.appendChild(tokenInput);
    controlDiv.appendChild(loadButton);
    controlDiv.appendChild(progress);
    document.body.appendChild(controlDiv);

    return { tokenInput, loadButton, progress };
}

async function getWorkflowStatus(badgeUrl, token) {
    const match = badgeUrl.match(/github\.com\/([^/]+)\/([^/]+)\/actions\/workflows\/([^/]+)\/badge\.svg/);
    if (!match) return null;

    const [, owner, repo, workflow] = match;
    const apiUrl = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/runs?per_page=1`;

    try {
        console.log('Fetching:', apiUrl);
        const headers = token ? { 'Authorization': `token ${token}` } : {};
        const response = await fetch(apiUrl, { headers });
        if (!response.ok) {
            console.error('API request failed:', response.status, await response.text());
            return null;
        }

        const data = await response.json();
        console.log('API response:', data);

        if (data.workflow_runs && data.workflow_runs.length > 0) {
            const latestRun = data.workflow_runs[0];
            return {
                conclusion: latestRun.conclusion || 'unknown',
                status: latestRun.status,
                timestamp: latestRun.updated_at
            };
        }

        return null;
    } catch (error) {
        console.error('Error fetching workflow status:', error);
        return null;
    }
}

function getSortKey(status) {
    if (!status) return 'z_unknown';

    // Sort successful builds first, then in-progress, then failed
    if (status.conclusion === 'success') return 'a_success_' + status.timestamp;
    if (status.status === 'in_progress') return 'b_running_' + status.timestamp;
    if (status.conclusion === 'failure') return 'c_failed_' + status.timestamp;

    // Other states like skipped, cancelled, etc.
    return 'd_other_' + status.conclusion + '_' + status.timestamp;
}

async function loadBadgesGradually(token, progressCallback) {
    // Initialize sort keys
    const badges = document.getElementsByClassName('badge');
    Array.from(badges).forEach(badge => {
        badge.setAttribute('sorttable_customkey', 'loading');
    });

    const badgeArray = Array.from(badges);
    const batchSize = 1; // number of badges per batch
    const delayMs = 200; // time between batches
    let processedCount = 0;

    async function loadBatch(startIndex) {
        const batch = badgeArray.slice(startIndex, startIndex + batchSize);
        console.log(`Loading batch starting at ${startIndex}`);

        // Process each badge in the batch
        for (const badge of batch) {
            const img = badge.querySelector('img');
            if (img && img.dataset.src) {
                console.log('Processing badge:', img.dataset.src);

                // Get workflow status first
                const status = await getWorkflowStatus(img.dataset.src, token);
                const sortKey = getSortKey(status);
                badge.setAttribute('sorttable_customkey', sortKey);
                console.log('Set sort key:', sortKey);

                // Then load the badge image
                img.src = img.dataset.src;

                // Update progress
                processedCount++;
                progressCallback(processedCount, badgeArray.length);
            }
        }

        // Schedule next batch if there are more badges
        if (startIndex + batchSize < badgeArray.length) {
            console.log(`Scheduling next batch in ${delayMs}ms`);
            return new Promise(resolve => {
                setTimeout(() => {
                    loadBatch(startIndex + batchSize).then(resolve);
                }, delayMs);
            });
        }
    }

    // Start loading first batch.
    await loadBatch(0);
}

// Initialize UI and handle load button click.
const { tokenInput, loadButton, progress } = addTokenUI();

loadButton.addEventListener('click', async () => {
    const token = tokenInput.value.trim();
    if (!token) {
        alert('Please enter a GitHub token. You can create one at https://github.com/settings/tokens with only "workflow" read permission.');
        return;
    }

    loadButton.disabled = true;
    loadButton.textContent = 'Loading...';

    try {
        await loadBadgesGradually(token, (current, total) => {
            progress.textContent = `Progress: ${current}/${total} (${Math.round(current/total*100)}%)`;
        });
    } catch (error) {
        console.error('Error loading badges:', error);
        alert('Error loading badges: ' + error.message);
    } finally {
        loadButton.disabled = false;
        loadButton.textContent = 'Load Build Status';
    }
});
