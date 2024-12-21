<!-- +page.svelte -->
<script lang="ts">
    import { onDestroy } from "svelte";

    type FileWithPreview = File & { preview?: string };

    // Use $state for reactive variables
    let searchQuery = $state('');
    let isDragging = $state(false);
    let files = $state<FileWithPreview[]>([]);
    let errorMessage = $state('');

    // Constants
    const ACCEPTED_FILE_TYPES = ['application/pdf', 'image/jpeg', 'image/png'];
    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

    function validateFile(file: File): string | null {
        if (!ACCEPTED_FILE_TYPES.includes(file.type)) {
            return 'Nur PDF, JPEG und PNG Dateien sind erlaubt.';
        }
        if (file.size > MAX_FILE_SIZE) {
            return 'Die Datei darf nicht größer als 10MB sein.';
        }
        return null;
    }

    function handleDragOver(event: DragEvent) {
        event.preventDefault();
        isDragging = true;
    }

    function handleDragLeave(event: DragEvent) {
        // Only leave drag state if we're not dragging over a child element
        if (event.currentTarget === event.target) {
            isDragging = false;
        }
    }

    async function handleFiles(fileList: FileList | null) {
        if (!fileList?.length) {
            return;
        }

        errorMessage = '';
        const file = fileList[0];

        // Validate file
        const error = validateFile(file);
        if (error) {
            errorMessage = error;
            return;
        }

        try {
            // Create file preview if it's an image
            if (file.type.startsWith('image/')) {
                const preview = URL.createObjectURL(file);
                files = [Object.assign(file, { preview })];
            } else {
                files = [file];
            }
        } catch (err) {
            errorMessage = 'Fehler beim Verarbeiten der Datei.';
            console.error('File processing error:', err);
        }
    }

    function handleDrop(event: DragEvent) {
        event.preventDefault();
        isDragging = false;
        handleFiles(event.dataTransfer?.files);
    }

    function handleFileSelect(event: Event) {
        const input = event.target as HTMLInputElement;
        handleFiles(input.files);
    }

    function handleSubmit(event: SubmitEvent) {
        event.preventDefault();
        if (!files.length) {
            errorMessage = 'Bitte wählen Sie zuerst eine Datei aus.';
            return;
        }
        if (!searchQuery.trim()) {
            errorMessage = 'Bitte beschreiben Sie Ihr Anliegen.';
            return;
        }
    }

    // Cleanup function for file previews
    onDestroy(() => {
        files.forEach(file => {
            if (file.preview) {
                URL.revokeObjectURL(file.preview);
            }
        });
    });
</script>

<section class="hero">
    <div class="hero-content">
        <h1>Mieterrechte einfach verstehen</h1>
        <p>KI-gestützte Analyse Ihrer Mietverträge. schnell, sicher und günstig.</p>

        <div
                class="upload-area"
                class:dragging={isDragging}
                class:has-error={errorMessage}
                ondragover={handleDragOver}
                ondragleave={handleDragLeave}
                ondrop={handleDrop}
                onkeydown={(e) => e.key === 'Enter' && document.getElementById('fileInput')?.click()}
                aria-dropeffect="copy"
                role="button"
                tabindex="0"
                aria-label="File Upload"
        >
            <input
                    type="file"
                    id="fileInput"
                    accept={ACCEPTED_FILE_TYPES.join(',')}
                    hidden
                    onchange={handleFileSelect}
            />
            <div class="upload-content">
                {#if files.length > 0}
                    <div class="file-preview">
                        {#if files[0].preview}
                            <img src={files[0].preview} alt="Vorschau"/>
                        {/if}
                        <span>{files[0].name}</span>
                    </div>
                {:else}
                    <span>Ziehen Sie Ihren Mietvertrag hierher oder</span>
                    <label for="fileInput">Datei auswählen</label>
                {/if}
            </div>
        </div>

        {#if errorMessage}
            <div class="error-message" role="alert">
                {errorMessage}
            </div>
        {/if}

        <form class="search-box" onsubmit={handleSubmit}>
            <input
                    type="text"
                    bind:value={searchQuery}
                    placeholder="Beschreiben Sie Ihr Anliegen..."
                    aria-label="Beschreiben Sie Ihr Anliegen"
            />
            <button type="submit">Prüfen</button>
        </form>
    </div>
</section>

<style>
    .hero {
        min-height: 90vh;
        display: flex;
        align-items: center;
        background: linear-gradient(rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0.5)),
        url('$lib/images/hero.webp') no-repeat center center;
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

    .error-message {
        background: rgba(255, 0, 0, 0.1);
        color: #ff3333;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        margin-top: 1rem;
    }

    .upload-area.has-error {
        border-color: #ff3333;
    }

    .file-preview {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .file-preview img {
        max-width: 100px;
        max-height: 100px;
        object-fit: contain;
    }
</style>
