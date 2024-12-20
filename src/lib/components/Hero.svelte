<!-- +page.svelte -->
<script>
	import { state } from 'svelte';

	const searchQuery = state('');
	const isDragging = state(false);

	// File handling
	let files = state([]);

	function handleDragOver(event) {
		event.preventDefault();
		$isDragging = true;
	}

	function handleDragLeave() {
		$isDragging = false;
	}

	function handleDrop(event) {
		event.preventDefault();
		$isDragging = false;
		$files = Array.from(event.dataTransfer.files);
	}

	function handleFileSelect(event) {
		$files = Array.from(event.target.files);
	}
</script>

<section class="hero">
    <div class="hero-content">
        <h1>Mieterrechte einfach verstehen</h1>
        <p>KI-gestützte Analyse Ihrer Mietverträge, schnell und günstig.</p>

        <div
                class="upload-area"
                class:dragging={$isDragging}
                on:dragover={handleDragOver}
                on:dragleave={handleDragLeave}
                on:drop={handleDrop}
        >
            <input
                    type="file"
                    id="fileInput"
                    hidden
                    on:change={handleFileSelect}
            />
            <div class="upload-content">
                <span>
                    {#if $files.length > 0}
                        {$files[0].name}
                    {:else}
                        Ziehen Sie Ihren Mietvertrag hierher oder
                    {/if}
                </span>
                <label for="fileInput">Datei auswählen</label>
            </div>
        </div>

        <form class="search-box">
            <input
                    type="text"
                    bind:value={$searchQuery}
                    placeholder="Beschreiben Sie Ihr Anliegen..."
            />
            <button type="submit">Prüfen</button>
        </form>
    </div>
</section>

<style>
    .hero {
        min-height: 80vh;
        display: flex;
        align-items: center;
        background: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)),
        url('$lib/images/hero.webp');
        background-size: cover;
        color: white;
        padding: 2rem;
    }

    .hero-content {
        max-width: 800px;
        margin: 0 auto;
    }

    h1 {
        font-size: 3rem;
        margin-bottom: 1rem;
    }

    .search-box {
        display: flex;
        gap: 1rem;
        margin-top: 2rem;
    }

    input {
        flex: 1;
        padding: 1rem;
        border-radius: 4px;
        border: none;
    }

    button {
        padding: 1rem 2rem;
        background: #FFD700;
        border: none;
        border-radius: 4px;
        font-weight: bold;
        cursor: pointer;
        transition: background-color 0.2s;
    }

    button:hover {
        background: #FFE44D;
    }

    .upload-area {
        background: rgba(255, 255, 255, 0.1);
        border: 2px dashed rgba(255, 255, 255, 0.3);
        border-radius: 8px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 2rem;
        transition: all 0.3s ease;
    }

    .upload-area.dragging {
        background: rgba(255, 255, 255, 0.2);
        border-color: #FFD700;
    }

    .upload-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1rem;
    }

    .upload-content label {
        color: #FFD700;
        cursor: pointer;
        text-decoration: underline;
    }

    .upload-content label:hover {
        color: #FFE44D;
    }
</style>
